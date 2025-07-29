import os
import json
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from studentbot.utils.text_formatter import get_translated_text

# Load the knowledge base
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
json_path = os.path.join(base_dir, "knowledge.json")
with open(json_path, "r", encoding="utf-8") as f:
    knowledge_base = json.load(f)


async def arrival_guide(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the arrival guide menu."""
    lang = context.user_data.get("lang", "en")
    buttons = [
        [get_translated_text(key, lang)]
        for key in knowledge_base["arrival_guide"].keys()
    ]
    reply_markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text(
        get_translated_text("arrival_guide_menu", lang), reply_markup=reply_markup
    )


async def arrival_guide_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the content of an arrival guide item."""
    lang = context.user_data.get("lang", "en")
    item_key = None
    for key, value in knowledge_base["arrival_guide"].items():
        if update.message.text.strip() == get_translated_text(key, lang):
            item_key = key
            break

    if item_key:
        item = knowledge_base["arrival_guide"][item_key]
        title = item["title"].get(lang, item["title"].get("en", ""))
        content = item["content"].get(lang, item["content"].get("en", ""))
        await update.message.reply_text(f"*{title}*\n\n{content}", parse_mode="Markdown")
    else:
        await update.message.reply_text(get_translated_text("item_not_found", lang))


def get_arrival_guide_handler():
    """Returns the arrival guide handler."""
    return [
        CommandHandler("arrival_guide", arrival_guide),
        MessageHandler(filters.TEXT & ~filters.COMMAND, arrival_guide_item),
    ]
