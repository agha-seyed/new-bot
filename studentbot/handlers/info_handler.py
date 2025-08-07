import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, Application
from telegram.error import TelegramError
from studentbot.utils.common import get_translated_text, sanitize_markdown  # Changed from text_formatter
from studentbot.utils.db_utils import get_user, log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

logger = logging.getLogger(__name__)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the help message with interactive buttons."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        keyboard = [
            [
                InlineKeyboardButton(get_translated_text("contact_button", lang), callback_data="contact"),
                InlineKeyboardButton(get_translated_text("about_button", lang), callback_data="about")
            ],
            [InlineKeyboardButton(get_translated_text("back_to_menu", lang), callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("help_text", lang)),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        async with AsyncSessionLocal() as session:
            user = await get_user(session, user_id)
            if user:
                interaction_data = [
                user_id,
                user.first_name,
                user.last_name or "N/A",
                user.age or 0,
                user.email or "N/A",
                user.field_of_study or "N/A",
                user.country or "N/A",
                "Help Command",
                "Requested help information",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
            await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await award_points_for_action(user_id, "interaction")
        async with AsyncSessionLocal() as session:
            await log_event(session, user_id, "help_accessed", "Requested help information")
        logger.info(f"✅ /help command used by user {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def contact_us(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the contact us message."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        keyboard = [
            [InlineKeyboardButton(get_translated_text("back_to_menu", lang), callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("contact_us_text", lang)),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        async with AsyncSessionLocal() as session:
            user = await get_user(session, user_id)
            if user:
                interaction_data = [
                user_id,
                user.first_name,
                user.last_name or "N/A",
                user.age or 0,
                user.email or "N/A",
                user.field_of_study or "N/A",
                user.country or "N/A",
                "Contact Command",
                "Requested contact information",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
            await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await award_points_for_action(user_id, "interaction")
        async with AsyncSessionLocal() as session:
            await log_event(session, user_id, "contact_accessed", "Requested contact information")
        logger.info(f"✅ /contact command used by user {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def about_us(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the about us message."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        keyboard = [
            [InlineKeyboardButton(get_translated_text("back_to_menu", lang), callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("about_us_text", lang)),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        async with AsyncSessionLocal() as session:
            user = await get_user(session, user_id)
            if user:
                interaction_data = [
                user_id,
                user.first_name,
                user.last_name or "N/A",
                user.age or 0,
                user.email or "N/A",
                user.field_of_study or "N/A",
                user.country or "N/A",
                "About Command",
                "Requested about information",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
            await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await award_points_for_action(user_id, "interaction")
        async with AsyncSessionLocal() as session:
            await log_event(session, user_id, "about_accessed", "Requested about information")
        logger.info(f"✅ /about command used by user {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback for help/contact/about buttons."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        if query.data == "contact":
            keyboard = [
                [InlineKeyboardButton(get_translated_text("back_to_menu", lang), callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("contact_us_text", lang)),
                parse_mode="MarkdownV2",
                reply_markup=reply_markup
            )
            action = "Contact Callback"
        elif query.data == "about":
            keyboard = [
                [InlineKeyboardButton(get_translated_text("back_to_menu", lang), callback_data="back_to_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("about_us_text", lang)),
                parse_mode="MarkdownV2",
                reply_markup=reply_markup
            )
            action = "About Callback"
        elif query.data == "back_to_menu":
            await query.message.reply_text(
                sanitize_markdown(get_translated_text("use_menu_command", lang)),
                parse_mode="MarkdownV2"
            )
            action = "Back to Menu"
        else:
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("invalid_selection", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ Invalid callback by user {user_id}: {query.data}")
            return
        
        async with AsyncSessionLocal() as session:
            user = await get_user(session, user_id)
            if user:
                interaction_data = [
                user_id,
                user.first_name,
                user.last_name or "N/A",
                user.age or 0,
                user.email or "N/A",
                user.field_of_study or "N/A",
                user.country or "N/A",
                action,
                f"Triggered {action.lower()}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
            await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await award_points_for_action(user_id, "interaction")
        async with AsyncSessionLocal() as session:
            await log_event(session, user_id, action.lower(), f"Triggered {action.lower()}")
        logger.info(f"✅ {action} triggered by user {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error handling callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

def get_info_handler():
    """Return the info handler."""
    return [
        CommandHandler("help", help_command),
        CommandHandler("contact", contact_us),
        CommandHandler("about", about_us),
        CallbackQueryHandler(info_callback, pattern="^(contact|about|back_to_menu)$"),
    ]
