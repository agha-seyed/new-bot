import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.error import TelegramError
from sqlalchemy import select
from studentbot.utils.common import get_translated_text, sanitize_markdown  # Changed from text_formatter
from studentbot.utils.db_utils import AsyncSessionLocal, get_user, log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.utils.ai_utils import smart_search
from studentbot.utils.redis_utils import cache_answer
from studentbot.utils.text_extractor import search_in_documents
from studentbot.utils.ai_utils import search_in_json
from studentbot.utils.alert_admin import notify_admin_unanswered
from studentbot.utils.models_db import Question
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

logger = logging.getLogger(__name__)

TITLE, DESCRIPTION, TOPIC, CONFIRMATION = range(4)

EMOJIS = {
    "title": "📄",
    "description": "📃",
    "topic": "🔍",
    "confirm": "✅",
    "cancel": "❌"
}

async def store_question(user_id: int, title: str, description: str, topic: str, answer: str = None) -> None:
    """Store question in the database."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                question = Question(
                    user_id=user_id,
                    title=title,
                    description=description,
                    topic=topic,
                    answer=answer,
                    status="answered" if answer else "pending"
                )
                session.add(question)
                await session.commit()
                logger.info(f"✅ Stored question for user {user_id}: {title}")
    except Exception as e:
        logger.error(f"❌ Error storing question for user {user_id}: {str(e)}")
        raise

async def start_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the question submission process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    context.user_data.clear()
    context.user_data["lang"] = lang
    
    try:
        await update.message.reply_text(
            f"{EMOJIS['title']} {sanitize_markdown(get_translated_text('question_title_prompt', lang))}",
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        logger.info(f"✅ User {user_id} started question submission")
        await award_points_for_action(user_id, "interaction")
        return TITLE
    except TelegramError as e:
        logger.error(f"❌ Telegram error starting question for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle question title input."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    context.user_data["question_title"] = update.message.text.strip()
    
    try:
        await update.message.reply_text(
            f"{EMOJIS['description']} {sanitize_markdown(get_translated_text('question_description_prompt', lang))}",
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ User {user_id} submitted question title")
        return DESCRIPTION
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling title for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle question description input."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    context.user_data["question_description"] = update.message.text.strip()
    
    try:
        keyboard = [
            [get_translated_text("scholarship_topic", lang), get_translated_text("housing_topic", lang)],
            [get_translated_text("deadlines_topic", lang), get_translated_text("migration_topic", lang)]
        ]
        reply_markup = InlineKeyboardMarkup.from_column([
            InlineKeyboardButton(text, callback_data=text.lower()) for row in keyboard for text in row
        ])
        await update.message.reply_text(
            f"{EMOJIS['topic']} {sanitize_markdown(get_translated_text('question_topic_prompt', lang))}",
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        logger.info(f"✅ User {user_id} submitted question description")
        return TOPIC
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling description for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def topic(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle question topic selection."""
    query = update.callback_query
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await query.answer()
        context.user_data["question_topic"] = query.data
        summary = f"""
*{sanitize_markdown(get_translated_text('summary_title', lang))}*
{EMOJIS['title']} *{sanitize_markdown(get_translated_text('title', lang))}*: {sanitize_markdown(context.user_data['question_title'])}
{EMOJIS['description']} *{sanitize_markdown(get_translated_text('description', lang))}*: {sanitize_markdown(context.user_data['question_description'])}
{EMOJIS['topic']} *{sanitize_markdown(get_translated_text('topic', lang))}*: {sanitize_markdown(context.user_data['question_topic'])}
\n{sanitize_markdown(get_translated_text('confirm_question_prompt', lang))}
        """
        buttons = [
            [InlineKeyboardButton(EMOJIS['confirm'], callback_data="confirm_question")],
            [InlineKeyboardButton(EMOJIS['cancel'], callback_data="cancel_question")]
        ]
        await query.edit_message_text(
            summary,
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        logger.info(f"✅ User {user_id} selected question topic: {context.user_data['question_topic']}")
        return CONFIRMATION
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling topic for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def confirm_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle question confirmation and processing."""
    query = update.callback_query
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await query.answer()
        user_data = context.user_data
        question_text = f"{user_data['question_title']} - {user_data['question_description']}"

        # Search in documents and JSON knowledge base
        text_answer = await search_in_documents(question_text) or await search_in_json(question_text)

        # Fallback to AI if no answer found
        if not text_answer:
            text_answer = await smart_search(question_text, user_id)

        # Store question in database
        await store_question(
            user_id=user_id,
            title=user_data["question_title"],
            description=user_data["question_description"],
            topic=user_data["question_topic"],
            answer=text_answer
        )

        # Save to Google Sheets
        user = await get_user(user_id)
        if user:
            interaction_data = [
                user_id,
                user.first_name,
                user.last_name or "N/A",
                user.age or 0,
                user.email or "N/A",
                user.field_of_study or "N/A",
                user.country or "N/A",
                "Question Submission",
                f"Title: {user_data['question_title']}, Topic: {user_data['question_topic']}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
            await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)

        await query.edit_message_text(
            sanitize_markdown(get_translated_text("ai_thinking", lang)),
            parse_mode="MarkdownV2"
        )

        # If no answer found, notify admin
        if not text_answer:
            await notify_admin_unanswered(question_text, user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text=sanitize_markdown(get_translated_text("admin_will_reply", lang)),
                parse_mode="MarkdownV2",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=sanitize_markdown(text_answer),
                parse_mode="MarkdownV2",
                reply_markup=ReplyKeyboardRemove()
            )
            await cache_answer(question_text, text_answer)

        # Award points and update level
        async with AsyncSessionLocal() as session:
            await add_score(session, user_id, 5)  # Assuming defined in gamification_handler.py
            await update_user_level(session, user_id)  # Assuming defined in gamification_handler.py

        await award_points_for_action(user_id, "question_submission")
        await log_event(user_id, "question_submitted", f"Title: {user_data['question_title']}, Topic: {user_data['question_topic']}")
        logger.info(f"✅ User {user_id} submitted question: {question_text}")
        context.user_data.clear()
        context.user_data["lang"] = lang
        return ConversationHandler.END
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error confirming question for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Unexpected error confirming question for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def cancel_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle question cancellation via callback."""
    query = update.callback_query
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await query.answer()
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("question_cancelled", lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        context.user_data["lang"] = lang
        logger.info(f"✅ User {user_id} cancelled question submission")
        return ConversationHandler.END
    except TelegramError as e:
        logger.error(f"❌ Telegram error cancelling question for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def cancel_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle question cancellation via command or text."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("question_cancelled", lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        context.user_data["lang"] = lang
        logger.info(f"✅ User {user_id} cancelled question submission")
        return ConversationHandler.END
    except TelegramError as e:
        logger.error(f"❌ Telegram error cancelling question for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

def get_question_handler():
    """Return the question handler."""
    return ConversationHandler(
        entry_points=[CommandHandler("question", start_question)],
        states={
            TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, title)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, description)],
            TOPIC: [CallbackQueryHandler(topic, pattern="^(scholarship|housing|deadlines|migration)$")],
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
