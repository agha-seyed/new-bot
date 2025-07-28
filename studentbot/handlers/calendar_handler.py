import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from utils.text_formatter import get_translated_text

# Load the calendar data
with open("studentbot/calendar.json", "r", encoding="utf-8") as f:
    calendar_data = json.load(f)


async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the calendar."""
    lang = context.user_data.get("lang", "en")
    keyboard = []
    for event in calendar_data["deadlines"]:
        keyboard.append(
            [
                InlineKeyboardButton(
                    f"{event['date']}: {event['event']}",
                    callback_data=f"event_{event['date']}",
                )
            ]
        )
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        get_translated_text("calendar", lang), reply_markup=reply_markup
    )


async def event_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the event callback."""
    query = update.callback_query
    await query.answer()
    date = query.data.split("_", 1)[1]
    for event in calendar_data["deadlines"]:
        if event["date"] == date:
            await query.edit_message_text(text=f"{event['date']}: {event['event']}")
            break


def get_calendar_handler():
    """Returns the calendar handler."""
    return [
        CommandHandler("calendar", calendar),
        CallbackQueryHandler(event_callback, pattern="^event_"),
    ]
