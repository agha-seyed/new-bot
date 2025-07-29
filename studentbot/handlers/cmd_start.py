import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from utils.text_formatter import get_translated_text  # ✅ اصلاح شده

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /start is issued."""
    keyboard = [["🇬🇧 English", "🇮🇹 Italiano", "🇮🇷 فارسی"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        "Please select your language:", reply_markup=reply_markup
    )
