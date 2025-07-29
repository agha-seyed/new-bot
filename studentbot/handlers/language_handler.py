import json
from telegram import Update
from telegram.ext import ContextTypes

from ..utils.text_formatter import get_translated_text


async def language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the language selection."""
    lang_map = {"🇬🇧 English": "en", "🇮🇹 Italiano": "it", "🇮🇷 فارسی": "fa"}
    lang = lang_map[update.message.text]
    context.user_data["lang"] = lang
    await update.message.reply_text(get_translated_text("welcome", lang))
