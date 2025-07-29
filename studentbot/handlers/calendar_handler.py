import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import TelegramError
from config import config
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.gamification_handler import award_points_for_action
from datetime import datetime

logger = logging.getLogger(__name__)

async def load_calendar_data():
    """Load the calendar data asynchronously."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "calendar.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"❌ Calendar file not found: {json_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"❌ Invalid calendar file format: {json_path}")
        raise

async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the calendar."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    try:
        calendar_data = await load_calendar_data()
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
            get_translated_text("calendar", lang),
            reply_markup=reply_markup,
        )
        await award_points_for_action(user_id, "interaction")
        await log_event(user_id, "calendar_accessed", "Opened calendar")
        logger.info(f"✅ Displayed calendar for user {user_id}")
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying calendar for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error displaying calendar for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))

async def event_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the event callback."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "en")
    user_id = query.from_user.id
    date = query.data.split("_", 1)[1]
    
    try:
        calendar_data = await load_calendar_data()
        matched = next(
            (event for event in calendar_data["deadlines"] if event["date"] == date),
            None,
        )
        
        if matched:
            message = f"📅 *{sanitize_markdown(matched['date'])}*: {sanitize_markdown(matched['event'])}\n"
            if matched.get("description"):
                message += f"\n{sanitize_markdown(matched['description'])}"
            
            # Store interaction in Google Sheets
            user = await db_utils.get_user(user_id)
            if user:
                interaction_data = [
                    user_id,
                    user["first_name"],
                    user["last_name"],
                    user["age"],
                    user["email"],
                    user.get("field_of_study", "N/A"),
                    user.get("country", "N/A"),
                    f"Calendar Event: {matched['event']}",
                    matched.get("description", "No description"),
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                ]
                await gsheets_client.add_consultation_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
            
            await award_points_for_action(user_id, "interaction")
            await log_event(user_id, "calendar_event_viewed", f"Event: {matched['event']}")
            await query.edit_message_text(text=message, parse_mode="MarkdownV2")
            logger.info(f"✅ Displayed calendar event '{date}' for user {user_id}")
        else:
            await query.edit_message_text(text=get_translated_text("event_not_found", lang))
            logger.warning(f"⚠️ Event not found for date: {date}, user: {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error in event callback for user {user_id}: {str(e)}")
        await query.edit_message_text(text=get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error in event callback for user {user_id}: {str(e)}")
        await query.edit_message_text(text=get_translated_text("error_occurred", lang))

def get_calendar_handler():
    """Return the calendar handler."""
    return [
        CommandHandler("calendar", calendar),
        CallbackQueryHandler(event_callback, pattern="^event_"),
    ]