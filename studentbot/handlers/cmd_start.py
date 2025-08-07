import logging
from typing import List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from studentbot.utils.common import get_translated_text, sanitize_markdown, get_available_languages
from studentbot.utils.db_utils import AsyncSessionLocal
from studentbot.utils.models_db import User
from sqlalchemy import update
from datetime import datetime, timezone
import studentbot.messages as messages

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command and prompt for language selection."""
    user_id = update.effective_user.id
    logger.info(f"🌟 User {user_id} triggered /start command.")

    try:
        # Update user's last_active timestamp
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    update(User)
                    .where(User.id == user_id)
                    .values(last_active=datetime.now(timezone.utc))
                )
        # Load available languages
        languages = await get_available_languages()
        
        # Create inline keyboard dynamically
        keyboard = [
            [InlineKeyboardButton(lang[0], callback_data=f"lang_{lang[1]}")]
            for lang in languages
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Multi-language prompt
        prompt = "\n".join(
            sanitize_markdown(messages.SELECT_LANGUAGE)
            for _, lang_code in languages
        )
        
        await update.message.reply_text(
            prompt,
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        
        # Reset only non-critical user_data
        context.user_data.clear()
        context.user_data["lang"] = "en"  # Default language
        logger.info(f"✅ User {user_id} user_data reset with default language 'en'.")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error in /start for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown("An error occurred. Please try again."),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error in /start for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown("An unexpected error occurred."),
            parse_mode="MarkdownV2"
        )
