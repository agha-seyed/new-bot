import logging
from typing import List, Tuple
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

async def get_available_languages() -> List[Tuple[str, str]]:
    """Load available languages dynamically from lang/ directory."""
    lang_dir = Path(__file__).resolve().parent.parent / "lang"
    languages = []
    try:
        for file in lang_dir.glob("*.json"):
            lang_code = file.stem
            lang_name = {
                "en": "🇬🇧 English",
                "fa": "🇮🇷 فارسی",
                "it": "🇮🇹 Italiano"
            }.get(lang_code, lang_code)
            languages.append((lang_name, lang_code))
        if not languages:
            logger.warning("⚠️ No language files found in lang/ directory")
        return languages
    except Exception as e:
        logger.error(f"❌ Error loading language files: {str(e)}")
        return [("🇬🇧 English", "en")]  # Fallback to English

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command and prompt for language selection."""
    user_id = update.effective_user.id
    logger.info(f"🌟 User {user_id} triggered /start command.")

    try:
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
            sanitize_markdown(get_translated_text("select_language", lang_code))
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
