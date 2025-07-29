import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes, CommandHandler

from ..utils.text_formatter import get_translated_text

logger = logging.getLogger(__name__)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the help message."""
    lang = context.user_data.get("lang", "en")
    logger.info(f"/help command used by {update.effective_user.id}")
    await update.message.reply_text(
        get_translated_text("help_text", lang),
        parse_mode=ParseMode.MARKDOWN
    )

async def contact_us(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the contact us message."""
    lang = context.user_data.get("lang", "en")
    logger.info(f"/contact command used by {update.effective_user.id}")
    await update.message.reply_text(
        get_translated_text("contact_us_text", lang),
        parse_mode=ParseMode.MARKDOWN
    )

async def about_us(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the about us message."""
    lang = context.user_data.get("lang", "en")
    logger.info(f"/about command used by {update.effective_user.id}")
    await update.message.reply_text(
        get_translated_text("about_us_text", lang),
        parse_mode=ParseMode.MARKDOWN
    )

def get_info_handler():
    """Returns the info handler."""
    return [
        CommandHandler("help", help_command),
        CommandHandler("contact", contact_us),
        CommandHandler("about", about_us),
    ]

def set_info_commands(application):
    """Adds info-related commands to the Telegram menu."""
    application.bot.set_my_commands([
        ("help", "📖 راهنما / Guida / Help"),
        ("contact", "📩 تماس با ما / Contattaci / Contact us"),
        ("about", "ℹ️ درباره ما / Chi siamo / About us"),
    ])
