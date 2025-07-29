import os
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.error import TelegramError
from config import config
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.gamification_handler import award_points_for_action
from datetime import datetime

logger = logging.getLogger(__name__)

async def load_knowledge_base():
    """Load the knowledge base asynchronously."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, "knowledge.json")
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"❌ Knowledge file not found: {json_path}")
        raise
    except json.JSONDecodeError:
        logger.error(f"❌ Invalid knowledge file format: {json_path}")
        raise

async def arrival_guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the arrival guide menu."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    try:
        knowledge_base = await load_knowledge_base()
        buttons = [
            [InlineKeyboardButton(get_translated_text(key, lang), callback_data=f"guide_{key}")]
            for key in knowledge_base["arrival_guide"].keys()
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        await update.message.reply_text(
            get_translated_text("arrival_guide_menu", lang),
            reply_markup=reply_markup,
        )
        await log_event(user_id, "arrival_guide_accessed", "Opened arrival guide menu")
        await award_points_for_action(user_id, "interaction")
        logger.info(f"✅ Displayed arrival guide menu for user {user_id}")
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying arrival guide for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error displaying arrival guide for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))

async def arrival_guide_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the content of an arrival guide item."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "en")
    user_id = query.from_user.id
    item_key = query.data.split("_", 1)[1]
    
    try:
        knowledge_base = await load_knowledge_base()
        item = knowledge_base["arrival_guide"].get(item_key)
        if not item:
            await query.edit_message_text(get_translated_text("item_not_found", lang))
            return
        
        title = item["title"].get(lang, item["title"].get("en", ""))
        content = item["content"].get(lang, item["content"].get("en", ""))
        message = f"*{sanitize_markdown(title)}*\n\n{sanitize_markdown(content)}"
        
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
                f"Arrival Guide: {title}",
                content,
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            ]
            await gsheets_client.add_consultation_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await query.edit_message_text(message, parse_mode="MarkdownV2")
        await award_points_for_action(user_id, "interaction")
        await log_event(user_id, "arrival_guide_item_viewed", f"Item: {title}")
        logger.info(f"✅ Displayed arrival guide item '{item_key}' for user {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying guide item for user {user_id}: {str(e)}")
        await query.edit_message_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error displaying guide item for user {user_id}: {str(e)}")
        await query.edit_message_text(get_translated_text("error_occurred", lang))

def get_arrival_guide_handler():
    """Return the arrival guide handler."""
    return [
        CommandHandler("arrival_guide", arrival_guide),
        CallbackQueryHandler(arrival_guide_item, pattern="^guide_"),
    ]