import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text

logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command and prompt for language selection."""
    user_id = update.effective_user.id
    logger.info(f"User {user_id} triggered /start command.")
    
    try:
        # Define available languages
        languages = [
            ("🇬🇧 English", "en"),
            ("🇮🇹 Italiano", "it"),
            ("🇮🇷 فارسی", "fa"),
        ]
        
        # Create keyboard dynamically
        keyboard = [[lang[0] for lang in languages]]
        reply_markup = ReplyKeyboardMarkup(
            keyboard, one_time_keyboard=True, resize_keyboard=True
        )
        
        # Multi-language prompt
        prompt = "\n".join(
            get_translated_text("select_language", lang_code)
            for _, lang_code in languages
        )
        
        await update.message.reply_text(prompt, reply_markup=reply_markup)
        
        # Reset only non-critical user_data
        context.user_data.clear()
        context.user_data["lang"] = "en"  # Default language
        logger.info(f"User {user_id} user_data reset with default language 'en'.")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error in /start for user {user_id}: {str(e)}")
        await update.message.reply_text("An error occurred. Please try again.")
    except Exception as e:
        logger.error(f"❌ Unexpected error in /start for user {user_id}: {str(e)}")
        await update.message.reply_text("An unexpected error occurred.")