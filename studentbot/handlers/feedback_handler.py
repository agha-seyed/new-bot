import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import AsyncSessionLocal, get_user, log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.utils.models_db import Feedback
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

logger = logging.getLogger(__name__)

async def store_feedback(user_id: int, rating: int) -> None:
    """Store feedback in the database using ORM."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                feedback = Feedback(user_id=user_id, rating=rating)
                session.add(feedback)
                await session.commit()
                logger.info(f"✅ Stored feedback for user {user_id}: {rating}")
    except Exception as e:
        logger.error(f"❌ Error storing feedback for user {user_id}: {str(e)}")
        raise

async def feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a feedback form to the user with star rating."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        keyboard = [
            [
                InlineKeyboardButton("⭐", callback_data="rating_1"),
                InlineKeyboardButton("⭐⭐", callback_data="rating_2"),
                InlineKeyboardButton("⭐⭐⭐", callback_data="rating_3"),
                InlineKeyboardButton("⭐⭐⭐⭐", callback_data="rating_4"),
                InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data="rating_5")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("feedback_prompt", lang)),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        logger.info(f"📝 Feedback form sent to user {user_id}")
        await award_points_for_action(user_id, "interaction")
    except TelegramError as e:
        logger.error(f"❌ Telegram error sending feedback form to user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def feedback_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the feedback callback."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    rating = int(query.data.split("_")[1])
    
    try:
        # Store feedback in database
        await store_feedback(user_id, rating)
        
        # Update user score
        async with AsyncSessionLocal() as session:
            await add_score(session, user_id, rating * 2)  # 2 points per star
            await update_user_level(session, user_id)
        
        # Store in Google Sheets
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
                "Feedback",
                f"Rating: {rating} stars",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
            await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        # Notify admin
        admin_chat_id = config.ADMIN_CHAT_ID
        if admin_chat_id:
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=sanitize_markdown(
                    get_translated_text("admin_feedback_received", lang).format(
                        user_id=user_id, rating=rating
                    )
                ),
                parse_mode="MarkdownV2"
            )
        
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("feedback_thanks", lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        await award_points_for_action(user_id, "feedback")
        await log_event(user_id, "feedback_submitted", f"Rating: {rating} stars")
        logger.info(f"✅ Feedback '{rating} stars' submitted by user {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling feedback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error handling feedback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

def get_feedback_handler():
    """Return the feedback handler."""
    return [
        CommandHandler("feedback", feedback),
        CallbackQueryHandler(feedback_callback, pattern="^rating_[1-5]$")
    ]
