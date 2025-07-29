import json
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.redis_utils import get_cached_answer, cache_answer
from studentbot.utils.ai_utils import smart_search
from studentbot.utils.db_utils import save_user_search

# Start command: Prompt user to enter query
async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("search_prompt", lang))

# Main search logic
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("lang", "en")
    user_id = update.message.from_user.id
    query = update.message.text.strip()

    if not query or len(query) < 3:
        await update.message.reply_text(get_translated_text("search_too_short", lang))
        return

    # Check Redis cache
    cached = get_cached_answer(query)
    if cached:
        await update.message.reply_text(f"✅ {get_translated_text('cached_result', lang)}\n\n{cached}")
        return

    # Send typing action
    await update.message.chat.send_action(action=ChatAction.TYPING)

    # Inform user
    await update.message.reply_text(get_translated_text("searching", lang))

    try:
        # Run semantic search
        answer = await smart_search(query, user_id)

        # Sanitize and send
        sanitized = sanitize_markdown(answer)
        await update.message.reply_text(sanitized, parse_mode="MarkdownV2")

        # Cache the result for future queries
        cache_answer(query, answer)

        # Save search activity
        save_user_search(user_id, query, answer)

    except Exception as e:
        print("Search Error:", e)
        await update.message.reply_text(get_translated_text("search_failed", lang))

# Handler function
def get_search_handler():
    return [
        CommandHandler("search", start_search),
        MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler),
    ]
