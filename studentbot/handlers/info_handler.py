import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, Application
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot.utils.gsheets import gsheets_client
from studentbot import config

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the help message with interactive buttons."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        keyboard = [
            [
                InlineKeyboardButton(get_translated_text("contact_button", lang), callback_data="contact"),
                InlineKeyboardButton(get_translated_text("about_button", lang), callback_data="about"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("help_text", lang)),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        logger.info(f"✅ /help command used by user {user_id}")
        await award_points_for_action(user_id, "interaction")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id,
                "N/A",
                "N/A",
                0,
                "N/A",
                "N/A",
                "N/A",
                "Help Command",
                "Requested help information",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
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
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("contact_us_text", lang)),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ /contact command used by user {user_id}")
        await award_points_for_action(user_id, "interaction")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id,
                "N/A",
                "N/A",
                0,
                "N/A",
                "N/A",
                "N/A",
                "Contact Command",
                "Requested contact information",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
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
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("about_us_text", lang)),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ /about command used by user {user_id}")
        await award_points_for_action(user_id, "interaction")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id,
                "N/A",
                "N/A",
                0,
                "N/A",
                "N/A",
                "N/A",
                "About Command",
                "Requested about information",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )


async def info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback for help/contact/about buttons."""
    query = update.callback_query
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await query.answer()
        if query.data == "contact":
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("contact_us_text", lang)),
                parse_mode="MarkdownV2"
            )
            action = "Contact Callback"
        elif query.data == "about":
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("about_us_text", lang)),
                parse_mode="MarkdownV2"
            )
            action = "About Callback"
        else:
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("invalid_selection", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ Invalid callback by user {user_id}: {query.data}")
            return
        
        logger.info(f"✅ {action} triggered by user {user_id}")
        await award_points_for_action(user_id, "interaction")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id,
                "N/A",
                "N/A",
                0,
                "N/A",
                "N/A",
                "N/A",
                action,
                f"Triggered {action.lower()}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling callback for user {user_id}: {str(e)}")
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
        CallbackQueryHandler(info_callback, pattern="^(contact|about)$"),
    ]


async def set_info_commands(application: Application) -> None:
    """Add info-related commands to the Telegram menu."""
    try:
        await application.bot.set_my_commands([
            ("help", get_translated_text("help_command_desc", "en")),
            ("contact", get_translated_text("contact_command_desc", "en")),
            ("about", get_translated_text("about_command_desc", "en")),
        ])
        logger.info("✅ Info commands set successfully")
    except TelegramError as e:
        logger.error(f"❌ Error setting info commands: {str(e)}")