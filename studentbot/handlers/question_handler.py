# studentbot/handlers/question_handler.py

import os
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler

from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.gsheets import add_question_to_sheet, save_admin_answer
from studentbot.utils.ai_utils import smart_search
from studentbot.utils.redis_utils import cache_answer
from studentbot.utils.file_search import search_in_documents
from studentbot.utils.json_search import search_json_knowledge
from studentbot.utils.admin_notify import notify_admin_unanswered
from studentbot.utils.db_utils import add_score, update_user_level

# States
TITLE, DESCRIPTION, TOPIC, CONFIRMATION = range(4)

EMOJIS = {
    "title": "📄",
    "description": "📃",
    "topic": "🔍",
    "confirm": "✅",
    "cancel": "❌"
}


async def start_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(f"{EMOJIS['title']} {get_translated_text('question_title_prompt', lang)}")
    return TITLE


async def title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["question_title"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(f"{EMOJIS['description']} {get_translated_text('question_description_prompt', lang)}")
    return DESCRIPTION


async def description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["question_description"] = update.message.text
    lang = context.user_data.get("lang", "en")
    topics = [["🎓 Scholarship", "🏠 Housing"], ["📅 Deadlines", "🌎 Migration"]]
    reply_markup = ReplyKeyboardMarkup(topics, resize_keyboard=True)
    await update.message.reply_text(f"{EMOJIS['topic']} {get_translated_text('question_topic_prompt', lang)}", reply_markup=reply_markup)
    return TOPIC


async def topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["question_topic"] = update.message.text
    lang = context.user_data.get("lang", "en")
    summary = f"*{get_translated_text('summary_title', lang)}*\n"
    summary += f"{EMOJIS['title']} *{get_translated_text('title', lang)}:* {sanitize_markdown(context.user_data['question_title'])}\n"
    summary += f"{EMOJIS['description']} *{get_translated_text('description', lang)}:* {sanitize_markdown(context.user_data['question_description'])}\n"
    summary += f"{EMOJIS['topic']} *{get_translated_text('topic', lang)}:* {sanitize_markdown(context.user_data['question_topic'])}\n"
    summary += f"\n{get_translated_text('confirm_question_prompt', lang)}"
    buttons = [
        [InlineKeyboardButton(EMOJIS['confirm'], callback_data="confirm_question")],
        [InlineKeyboardButton(EMOJIS['cancel'], callback_data="cancel_question")]
    ]
    await update.message.reply_text(summary, parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(buttons))
    return CONFIRMATION


async def confirm_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "en")
    user_data = context.user_data
    user_id = query.from_user.id
    question = f"{user_data['question_title']} - {user_data['question_description']}"

    # 1. ذخیره در Google Sheets
    add_question_to_sheet([
        user_id,
        user_data["question_title"],
        user_data["question_description"],
        user_data["question_topic"],
        datetime.now().isoformat()
    ])

    await query.edit_message_text(get_translated_text("ai_thinking", lang))

    # 2. جستجو در فایل‌های PDF، Word، JSON
    text_answer = search_in_documents(question) or search_json_knowledge(question)
    
    # 3. اگر نبود: استفاده از هوش مصنوعی
    if not text_answer:
        text_answer = await smart_search(question, user_id)

    # 4. اگر باز هم نبود: اطلاع به ادمین
    if not text_answer:
        await notify_admin_unanswered(question, user_id)
        await context.bot.send_message(
            chat_id=user_id,
            text=get_translated_text("admin_will_reply", lang)
        )
    else:
        # 5. پاسخ نهایی به کاربر
        await context.bot.send_message(chat_id=user_id, text=text_answer)
        await cache_answer(question, text_answer)

    # 6. امتیازدهی و ارتقا سطح
    add_score(user_id, 5)
    update_user_level(user_id)

    return ConversationHandler.END


async def cancel_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.callback_query.answer()
    lang = context.user_data.get("lang", "en")
    await update.callback_query.edit_message_text(get_translated_text("question_cancelled", lang))
    return ConversationHandler.END


async def cancel_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("question_cancelled", lang))
    return ConversationHandler.END


def get_question_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("question", start_question)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            TOPIC: [MessageHandler(filters.TEXT & ~filters.COMMAND, topic)],
            CONFIRMATION: [
                CallbackQueryHandler(confirm_question, pattern="^confirm_question$"),
                CallbackQueryHandler(cancel_question_callback, pattern="^cancel_question$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, cancel_question),
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_question)
        ],
        allow_reentry=True
    )
