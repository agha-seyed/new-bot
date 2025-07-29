# studentbot/handlers/question_handler.py

import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.gsheets import add_user_to_sheet
from studentbot.utils.db_utils import add_score, update_user_level

# States
TITLE, DESCRIPTION, TOPIC, CONFIRMATION = range(4)

# Emojis for fun and clarity
EMOJIS = {
    "title": "📄",
    "description": "📃",
    "topic": "🔍",
    "confirm": "✅",
    "cancel": "❌"
}

async def start_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    context.user_data.clear()
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
    topics = [
        ["🎓 Scholarship", "🏠 Housing"],
        ["📅 Deadlines", "🌎 Migration"],
    ]
    reply_markup = ReplyKeyboardMarkup(topics, resize_keyboard=True)
    await update.message.reply_text(f"{EMOJIS['topic']} {get_translated_text('question_topic_prompt', lang)}", reply_markup=reply_markup)
    return TOPIC

async def topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["question_topic"] = update.message.text
    lang = context.user_data.get("lang", "en")

    summary = f"\n\n*{get_translated_text('summary_title', lang)}*\n"
    summary += f"{EMOJIS['title']} *{get_translated_text('title', lang)}:* {sanitize_markdown(context.user_data['question_title'])}\n"
    summary += f"{EMOJIS['description']} *{get_translated_text('description', lang)}:* {sanitize_markdown(context.user_data['question_description'])}\n"
    summary += f"{EMOJIS['topic']} *{get_translated_text('topic', lang)}:* {sanitize_markdown(context.user_data['question_topic'])}\n"
    summary += f"\n{get_translated_text('confirm_question_prompt', lang)}"

    buttons = [
        [InlineKeyboardButton(EMOJIS['confirm'], callback_data="confirm_question")],
        [InlineKeyboardButton(EMOJIS['cancel'], callback_data="cancel_question")],
    ]
    await update.message.reply_text(summary, parse_mode="MarkdownV2", reply_markup=InlineKeyboardMarkup(buttons))
    return CONFIRMATION

async def confirm_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "en")
    user_data = context.user_data
    user_id = query.from_user.id

    # Save to Google Sheets
    add_user_to_sheet("questions", [
        user_id,
        user_data["question_title"],
        user_data["question_description"],
        user_data["question_topic"],
        datetime.now().isoformat()
    ])

    # Notify admin with an inline reply button
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")
    if admin_chat_id:
        reply_button = InlineKeyboardMarkup([[
            InlineKeyboardButton("Reply", callback_data=f"reply_question_{user_id}")
        ]])
        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=f"New question:\n\nTitle: {user_data['question_title']}\nDescription: {user_data['question_description']}\nTopic: {user_data['question_topic']}",
            reply_markup=reply_button
        )

    # Score
    add_score(user_id, 5)
    update_user_level(user_id)
    await query.edit_message_text(get_translated_text("question_complete", lang))
    return ConversationHandler.END

async def cancel_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "en")
    await query.edit_message_text(get_translated_text("question_cancelled", lang))
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
                MessageHandler(filters.TEXT & ~filters.COMMAND, cancel_question),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_question),
            MessageHandler(filters.Regex("^cancel_question$"), cancel_question),
        ],
        allow_reentry=True,
    )
