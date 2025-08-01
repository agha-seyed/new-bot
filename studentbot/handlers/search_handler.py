import logging
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.error import TelegramError
from sqlalchemy import select
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.redis_utils import redis_client
from studentbot.utils.ai_utils import smart_search
from studentbot.utils.db_utils import get_user, AsyncSessionLocal, log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.utils.models_db import SearchHistory
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

logger = logging.getLogger(__name__)

async def save_user_search(session: AsyncSession, user_id: int, query: str, answer: str) -> None:
    """Save user search to the database."""
    try:
        async with session.begin():
            search = SearchHistory(
                user_id=user_id,
                query=query,
                answer=answer
            )
            session.add(search)
            await session.commit()
            logger.info(f"✅ Saved search for user {user_id}: {query}")
    except Exception as e:
        logger.error(f"❌ Error saving search for user {user_id}: {str(e)}")
        raise

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
        await log_event(user_id, "search_started", "Started search process")
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

        # Initialize Redis client if not already done
        if not redis_client.client:
            await redis_client.initialize()

        # Check Redis cache
        cached = await redis_client.get_cached_answer(query)
        if cached:
            keyboard = [[InlineKeyboardButton(get_translated_text("search_again", lang), callback_data="search_again")]]
            await update.message.reply_text(
                f"✅ {sanitize_markdown(get_translated_text('cached_result', lang))}\n\n{sanitize_markdown(cached)}",
                parse_mode="MarkdownV2",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            async with AsyncSessionLocal() as session:
                user = await get_user(session, user_id)
                if user:
                    interaction_data = [
                        user_id,
                        user.first_name,
                        user.last_name or "N/A",
                        user.age or 0,
                        user.email or "N/A",
                        user.field_of_study or "N/A",
                        user.country or "N/A",
                        "Search (Cached)",
                        f"Cached search result for {query}",
                        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    ]
                    await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
            await award_points_for_action(user_id, "interaction")
            await log_event(user_id, "search_cached", f"Cached search result for {query}")
            logger.info(f"✅ User {user_id} received cached search result for query: {query}")
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
        await redis_client.cache_answer(query, answer)

        # Save search activity
        async with AsyncSessionLocal() as session:
            await save_user_search(session, user_id, query, answer)
            user = await get_user(session, user_id)
            if user:
                interaction_data = [
                    user_id,
                    user.first_name,
                    user.last_name or "N/A",
                    user.age or 0,
                    user.email or "N/A",
                    user.field_of_study or "N/A",
                    user.country or "N/A",
                    "Search",
                    f"New search for {query}",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
                await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)

        await award_points_for_action(user_id, "search")
        await log_event(user_id, "search_completed", f"New search for {query}")
        logger.info(f"✅ User {user_id} received search result for query: {query}")
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
            await award_points_for_action(user_id, "interaction")
            await log_event(user_id, "search_again", "Requested to search again")
            logger.info(f"✅ User {user_id} requested to search again")
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
