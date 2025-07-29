import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from studentbot.utils.text_formatter import get_translated_text

# Load the calendar data from the correct path
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
json_path = os.path.join(base_dir, "calendar.json")
with open(json_path, "r", encoding="utf-8") as f:
    calendar_data = json.load(f)


async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the calendar."""
    lang = context.user_data.get("lang", "en")
    keyboard = [
        [
            InlineKeyboardButton(
                f"{event['date']}: {event['event']}",
                callback_data=f"event_{event['date']}",
            )
        ]
        for event in calendar_data.get("deadlines", [])
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        get_translated_text("calendar", lang), reply_markup=reply_markup
    )


async def event_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the event callback."""
    query = update.callback_query
    await query.answer()

    date = query.data.split("_", 1)[1]
    matched = next(
        (event for event in calendar_data["deadlines"] if event["date"] == date),
        None,
    )

    if matched:
        await query.edit_message_text(text=f"{matched['date']}: {matched['event']}")
    else:
        await query.edit_message_text(text="⚠️ Event not found.")


def get_calendar_handler():
    """Returns the calendar handler."""
    return [
        CommandHandler("calendar", calendar),
        CallbackQueryHandler(event_callback, pattern="^event_"),
    ]
