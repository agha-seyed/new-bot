from telegram import Update
from telegram.ext import ContextTypes, CommandHandler

from studentbot.utils.text_formatter import get_translated_text


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the help message."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("help_text", lang))


async def contact_us(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the contact us message."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("contact_us_text", lang))


async def about_us(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the about us message."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("about_us_text", lang))


def get_info_handler():
    """Returns the info handler."""
    return [
        CommandHandler("help", help_command),
        CommandHandler("contact", contact_us),
        CommandHandler("about", about_us),
    ]
