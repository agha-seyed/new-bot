from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from studentbot.utils.text_formatter import get_translated_text


async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the search process."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("search_prompt", lang))


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the search query."""
    lang = context.user_data.get("lang", "en")
    query = update.message.text
    # TODO: Implement search logic
    await update.message.reply_text(f"You searched for: {query}")


def get_search_handler():
    """Returns the search handler."""
    return [
        CommandHandler("search", start_search),
        MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler),
    ]
