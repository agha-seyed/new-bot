from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters

from studentbot.utils.text_formatter import get_translated_text


async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts the search process."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("search_prompt", lang))


import json
from sentence_transformers import util

from studentbot.handlers.ai_handler import model

async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the search query."""
    lang = context.user_data.get("lang", "en")
    query = update.message.text

    # Load the Q&A data
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    qna_file_path = os.path.join(base_dir, "qna.json")
    with open(qna_file_path, "r", encoding="utf-8") as f:
        qna_data = json.load(f)

    # Find the best match for the user's query
    questions = [q["q"] for q in qna_data["questions"]]
    query_embedding = model.encode(query, convert_to_tensor=True)
    best_match_score = 0
    best_match_index = -1
    for i, q in enumerate(questions):
        q_embedding = model.encode(q, convert_to_tensor=True)
        score = util.pytorch_cos_sim(query_embedding, q_embedding)
        if score > best_match_score:
            best_match_score = score
            best_match_index = i

    if best_match_score > 0.5:
        answer = qna_data["questions"][best_match_index]["a"]
    else:
        answer = "I'm sorry, I don't have an answer to that question."

    await update.message.reply_text(answer)


def get_search_handler():
    """Returns the search handler."""
    return [
        CommandHandler("search", start_search),
        MessageHandler(filters.TEXT & ~filters.COMMAND, search_handler),
    ]
