import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes

from studentbot.utils.text_formatter import get_translated_text  # ✅ مسیر absolute و امن

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message when the command /start is issued."""
    # Display language selection
    keyboard = [["🇬🇧 English", "🇮🇹 Italiano", "🇮🇷 فارسی"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(
        "Please select your language:\nلطفاً زبان خود را انتخاب کنید:\nPer favore seleziona la tua lingua:",
        reply_markup=reply_markup,
    )

    # Optional: reset user data on restart
    context.user_data.clear()
