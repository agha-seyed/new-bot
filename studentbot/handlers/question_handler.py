import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.gsheets import gsheets_client
from studentbot.utils.ai_utils import smart_search
from studentbot.utils.redis_utils import cache_answer
from studentbot.utils.file_search import search_in_documents
from studentbot.utils.json_search import search_json_knowledge
from studentbot.utils.admin_notify import notify_admin_unanswered
from studentbot.utils.db_utils import add_score, update_user_level, AsyncSessionLocal
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

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
    """Start the question submission process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    context.user_data.clear()
    
    try:
        await update.message.reply_text(
            f"{EMOJIS['title']} {sanitize_markdown(get_translated_text('question_title_prompt', lang))}",
            parse_mode="MarkdownV2"
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
        question = f"{user_data['question_title']} - {user_data['question_description']}"

        # Save to Google Sheets
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id,
                user_data["question_title"],
                user_data["question_description"],
                user_data["question_topic"],
                "N/A",
                "N/A",
                "N/A",
                "Question Submission",
                "Submitted question",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )

        await query.edit_message_text(
            sanitize_markdown(get_translated_text("ai_thinking", lang)),
            parse_mode="MarkdownV2"
        )

        # Search in documents and JSON knowledge base
        text_answer = search_in_documents(question) or search_json_knowledge(question)

        # Fallback to AI if no answer found
        if not text_answer:
            text_answer = await smart_search(question, user_id)

        # If still no answer, notify admin
        if not text_answer:
            await notify_admin_unanswered(question, user_id)
            await context.bot.send_message(
                chat_id=user_id,
                text=sanitize_markdown(get_translated_text("admin_will_reply", lang)),
                parse_mode="MarkdownV2"
            )
        else:
            await context.bot.send_message(
                chat_id=user_id,
                text=sanitize_markdown(text_answer),
                parse_mode="MarkdownV2"
            )
            await cache_answer(question, text_answer)

        # Award points and update level
        async with AsyncSessionLocal() as session:
            await add_score(session, user_id, 5)
            await update_user_level(session, user_id)

        logger.info(f"✅ User {user_id} submitted question: {question}")
        await award_points_for_action(user_id, "question_submission")
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
            parse_mode="MarkdownV2"
        )
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
            parse_mode="MarkdownV2"
        )
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