from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from ..utils.text_formatter import get_translated_text
from ..utils.redis_utils import get_cached_answer, cache_answer


async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the search process."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("search_prompt", lang))


import json
from sentence_transformers import util

from .ai_handler import model

from ..utils.ai_utils import smart_search

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the search query."""
    lang = context.user_data.get("lang", "en")
    query = update.message.text
    user_id = update.message.from_user.id

    await update.message.reply_text(get_translated_text("searching", lang))
    answer = await smart_search(query, user_id)
    await update.message.reply_text(answer)


def get_search_handler():
    """Returns the search handler."""
    return [
        CommandHandler("search", start_search),
        MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler),
    ]
