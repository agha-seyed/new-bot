import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import TelegramError
from studentbot import config
from studentbot.utils.common import get_translated_text, sanitize_markdown  # Changed from text_formatter
from studentbot.utils.db_utils import log_event, get_user
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from datetime import datetime

logger = logging.getLogger(__name__)

async def load_json_data(file_name: str):
    """Load JSON data asynchronously."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, file_name)
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"❌ JSON file not found: {json_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"❌ Invalid JSON file format: {json_path}")
        raise

async def arrival_guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the arrival guide menu."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    try:
        knowledge_base = await load_json_data("knowledge.json")
        buttons = [
            [InlineKeyboardButton(get_translated_text(key, lang), callback_data=f"guide_{key}")]
            for key in knowledge_base["arrival_guide"].keys()
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("arrival_guide_menu", lang)),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        async with AsyncSessionLocal() as session:
            await log_event(session, user_id, "arrival_guide_accessed", "Opened arrival guide menu")
        await award_points_for_action(user_id, "interaction")
        logger.info(f"✅ Displayed arrival guide menu for user {user_id}")
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying arrival guide for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error displaying arrival guide for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def calendar(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the calendar."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    try:
        calendar_data = await load_json_data("calendar.json")
        keyboard = [
            [
                InlineKeyboardButton(
                    f"📅 {event['date']}: {sanitize_markdown(event['event'])}",
                    callback_data=f"event_{event['date']}"
                )
            ]
            for event in calendar_data.get("deadlines", [])
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("calendar", lang)),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        await award_points_for_action(user_id, "interaction")
        async with AsyncSessionLocal() as session:
            await log_event(session, user_id, "calendar_accessed", "Opened calendar")
        logger.info(f"✅ Displayed calendar for user {user_id}")
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying calendar for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error displaying calendar for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def guide_item_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the content of an arrival guide item."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "en")
    user_id = query.from_user.id
    item_key = query.data.split("_", 1)[1]
    
    try:
        knowledge_base = await load_json_data("knowledge.json")
        item = knowledge_base["arrival_guide"].get(item_key)
        if not item:
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("item_not_found", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ Guide item not found: {item_key}, user: {user_id}")
            return
        
        title = item["title"].get(lang, item["title"].get("en", ""))
        content = item["content"].get(lang, item["content"].get("en", ""))
        message = f"📖 *{sanitize_markdown(title)}*\n\n{sanitize_markdown(content)}"
        
        # Store interaction in Google Sheets
        user = await get_user(user_id)
        if user:
            interaction_data = [
                user_id,
                user.first_name,
                user.last_name or "N/A",
                user.age or 0,
                user.email or "N/A",
                user.field_of_study or "N/A",
                user.country or "N/A",
                f"Arrival Guide: {title}",
                content,
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            ]
            await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await query.edit_message_text(
            message,
            parse_mode="MarkdownV2"
        )
        await award_points_for_action(user_id, "interaction")
        async with AsyncSessionLocal() as session:
            await log_event(session, user_id, "arrival_guide_item_viewed", f"Item: {title}")
        logger.info(f"✅ Displayed arrival guide item '{item_key}' for user {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying guide item for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error displaying guide item for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def event_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the calendar event callback."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "en")
    user_id = query.from_user.id
    date = query.data.split("_", 1)[1]
    
    try:
        calendar_data = await load_json_data("calendar.json")
        matched = next(
            (event for event in calendar_data["deadlines"] if event["date"] == date),
            None
        )
        
        if matched:
            message = f"📅 *{sanitize_markdown(matched['date'])}*: {sanitize_markdown(matched['event'])}\n"
            if matched.get("description"):
                message += f"\n{sanitize_markdown(matched['description'])}"
            
            # Store interaction in Google Sheets
            user = await get_user(user_id)
            if user:
                interaction_data = [
                    user_id,
                    user.first_name,
                    user.last_name or "N/A",
                    user.age or 0,
                    user.email or "N/A",
                    user.field_of_study or "N/A",
                    user.country or "N/A",
                    f"Calendar Event: {matched['event']}",
                    matched.get("description", "No description"),
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                ]
                await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
            
            await award_points_for_action(user_id, "interaction")
            async with AsyncSessionLocal() as session:
                await log_event(session, user_id, "calendar_event_viewed", f"Event: {matched['event']}")
            await query.edit_message_text(
                text=message,
                parse_mode="MarkdownV2"
            )
            logger.info(f"✅ Displayed calendar event '{date}' for user {user_id}")
        else:
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("event_not_found", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ Event not found for date: {date}, user: {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error in event callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error in event callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

def get_guide_handler():
    """Return the guide handler for both arrival guide and calendar."""
    return [
        CommandHandler("arrival_guide", arrival_guide),
        CommandHandler("calendar", calendar),
        CallbackQueryHandler(guide_item_callback, pattern="^guide_"),
        CallbackQueryHandler(event_callback, pattern="^event_"),
    ]
