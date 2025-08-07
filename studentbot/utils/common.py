import os
import json
import logging
from pathlib import Path
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

def sanitize_markdown(text: str) -> str:
    """Sanitize text for Telegram MarkdownV2."""
    if not text:
        return ""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text

def get_translated_text(key: str, lang: str = "en") -> str:
    """Retrieve translated text from JSON files."""
    lang_dir = Path(__file__).resolve().parent.parent / "lang"
    lang_file = lang_dir / f"{lang}.json"
    
    try:
        if not lang_file.exists():
            logger.warning(f"⚠️ Language file {lang_file} not found, falling back to 'en'")
            lang_file = lang_dir / "en.json"
        
        with open(lang_file, "r", encoding="utf-8") as f:
            translations = json.load(f)
        
        result = translations
        for part in key.split("."):
            result = result.get(part, part)
        
        if isinstance(result, dict):
            return result.get(lang, result.get("en", key))
        return result if isinstance(result, str) else key
    except Exception as e:
        logger.error(f"❌ Error loading translations for {lang}: {str(e)}")
        return key

async def get_available_languages() -> list[tuple[str, str]]:
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

async def prompt(update, context, prompt_text: str, next_state: int) -> int:
    """Send a prompt message and return the next state."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")

    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text(prompt_text, lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        logger.info(f"✅ Prompt {prompt_text} sent to user {user_id}")
        return next_state
    except TelegramError as e:
        logger.error(f"❌ Telegram error sending prompt {prompt_text} to user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
