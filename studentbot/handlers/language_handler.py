import json
import logging
from telegram import Update
from telegram.ext import ContextTypes

from studentbot.utils.text_formatter import get_translated_text

# 🎯 تنظیمات لگ‌گیری
logger = logging.getLogger(__name__)

async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the language selection."""
    lang_map = {"🇬🇧 English": "en", "🇮🇹 Italiano": "it", "🇮🇷 فارسی": "fa"}
    selected = update.message.text.strip()

    logger.info(f"User {update.effective_user.id} selected language: {selected}")

    if selected not in lang_map:
        logger.warning(f"Invalid language selection by user {update.effective_user.id}: {selected}")
        await update.message.reply_text("❌ Invalid selection. Please choose a valid language.")
        return

    lang = lang_map[selected]
    context.user_data["lang"] = lang
    logger.info(f"Language set to {lang} for user {update.effective_user.id}")

    await update.message.reply_text(get_translated_text("welcome", lang))
