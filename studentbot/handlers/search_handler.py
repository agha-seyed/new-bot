import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.redis_utils import get_cached_answer, cache_answer
from studentbot.utils.ai_utils import smart_search
from studentbot.utils.db_utils import save_user_search, AsyncSessionLocal
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to enter a search query."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("search_prompt", lang)),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ User {user_id} started search")
        await award_points_for_action(user_id, "interaction")
    except TelegramError as e:
        logger.error(f"❌ Telegram error starting search for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle search queries."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    query = update.message.text.strip()
    
    try:
        if not query or len(query) < 3:
            await update.message.reply_text(
                sanitize_markdown(get_translated_text("search_too_short", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ Search query too short by user {user_id}: {query}")
            return

        # Check Redis cache
        cached = await get_cached_answer(query)
        if cached:
            keyboard = [[InlineKeyboardButton(get_translated_text("search_again", lang), callback_data="search_again")]]
            await update.message.reply_text(
                f"✅ {sanitize_markdown(get_translated_text('cached_result', lang))}\n\n{sanitize_markdown(cached)}",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            logger.info(f"✅ User {user_id} received cached search result for query: {query}")
            await award_points_for_action(user_id, "interaction")
            await gsheets_client.add_interaction_to_sheet(
                config.QUESTIONS_SHEET_NAME,
                [
                    user_id,
                    query,
                    cached,
                    0,
                    "N/A",
                    "N/A",
                    "N/A",
                    "Search (Cached)",
                    f"Cached search result for {query}",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
            )
            return

        # Send typing action
        await update.message.chat.send_action(action=ChatAction.TYPING)

        # Inform user
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("searching", lang)),
            parse_mode="MarkdownV2"
        )

        # Run semantic search
        answer = await smart_search(query, user_id)

        # Sanitize and send
        sanitized = sanitize_markdown(answer)
        keyboard = [[InlineKeyboardButton(get_translated_text("search_again", lang), callback_data="search_again")]]
        await update.message.reply_text(
            sanitized,
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        # Cache the result
        await cache_answer(query, answer)

        # Save search activity
        async with AsyncSessionLocal() as session:
            await save_user_search(session, user_id, query, answer)

        logger.info(f"✅ User {user_id} received search result for query: {query}")
        await award_points_for_action(user_id, "search")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id,
                query,
                answer,
                0,
                "N/A",
                "N/A",
                "N/A",
                "Search",
                f"New search for {query}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
    except TelegramError as e:
        logger.error(f"❌ Telegram error during search for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("search_failed", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error during search for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("search_failed", lang)),
            parse_mode="MarkdownV2"
        )


async def search_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle search-related callbacks."""
    query = update.callback_query
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await query.answer()
        if query.data == "search_again":
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("search_prompt", lang)),
                parse_mode="MarkdownV2"
            )
            logger.info(f"✅ User {user_id} requested to search again")
            await award_points_for_action(user_id, "interaction")
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling search callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )


def get_search_handler():
    """Return the search handler."""
    return [
        CommandHandler("search", start_search),
        MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler),
        CallbackQueryHandler(search_callback, pattern="^search_again$")
    ]