import os
import json
import time
import logging
import asyncio
from datetime import datetime
from studentbot.utils.text_extractor import search_in_documents
from studentbot.utils.redis_utils import redis_client
from studentbot.utils.alert_admin import notify_admin_unanswered
from studentbot.utils.gsheets import gsheets_client
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot.utils.gpt_utils import ask_gpt
from studentbot.utils.models import model, qa_pipeline, initialize_models

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def search_in_json(question: str, lang: str = "fa") -> dict | None:
    """Searches for an answer in the local JSON knowledge base."""
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        qna_file_path = os.path.join(base_dir, "qna.json")
        with open(qna_file_path, "r", encoding="utf-8") as f:
            qna_data = json.load(f)

        if not model:
            initialize_models()

        from sentence_transformers import util  # Import inside function to avoid circular import
        questions = [q["q"] for q in qna_data["questions"]]
        question_embedding = model.encode(question, convert_to_tensor=True)
        best_match_score = 0
        best_match_index = -1

        for i, q in enumerate(questions):
            q_embedding = model.encode(q, convert_to_tensor=True)
            score = util.pytorch_cos_sim(question_embedding, q_embedding).item()
            if score > best_match_score:
                best_match_score = score
                best_match_index = i

        logger.info(f"✅ JSON search for question: {question}, Best match score: {best_match_score}")

        if best_match_score > 0.7:
            answer_entry = qna_data["questions"][best_match_index]
            answer = answer_entry["a"].get(lang, answer_entry["a"].get("fa", ""))
            category = answer_entry.get("category", "General")
            return {
                "answer": answer,
                "source": "json",
                "score": best_match_score,
                "category": category
            }
        return None
    except FileNotFoundError:
        logger.error(f"❌ JSON file not found: {qna_file_path}")
        return None
    except Exception as e:
        logger.error(f"❌ Error in JSON search: {str(e)}")
        return None

async def ask_huggingface(question: str) -> dict | None:
    """Asks a question to the Hugging Face QA pipeline."""
    try:
        if not qa_pipeline:
            initialize_models()
        
        context = "The Student Helper Bot is a Telegram bot designed to help international students, especially in Perugia."
        result = qa_pipeline(question=question, context=context)
        return {
            "answer": result["answer"],
            "source": "huggingface",
            "score": result["score"]
        }
    except Exception as e:
        logger.error(f"❌ Hugging Face error: {str(e)}")
        return None

async def smart_search(question: str, user_id: int, lang: str = "fa") -> str:
    """Performs a smart search for a user's question."""
    start = time.time()
    
    try:
        # Initialize Redis client if not already done
        if not redis_client.client:
            await redis_client.initialize()
        
        # 1. Try cache first
        cached = await redis_client.get_cached_answer(question)
        if cached:
            await award_points_for_action(user_id, "interaction")
            await gsheets_client.add_interaction_to_sheet(
                config.QUESTIONS_SHEET_NAME,
                [
                    user_id,
                    question,
                    cached,
                    0,
                    "N/A",
                    "N/A",
                    "N/A",
                    "Search (Cached)",
                    f"Cached search result for {question}",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
            )
            end = time.time()
            return f"📦 *{sanitize_markdown(get_translated_text('cached_result', lang))}*\n\n{sanitize_markdown(cached)}\n\n⏱️ *{sanitize_markdown(get_translated_text('response_time', lang))}*: {round(end - start, 2)} s"

        # 2. JSON Knowledge Base
        json_result = await search_in_json(question, lang)
        if json_result:
            await redis_client.cache_answer(question, json_result["answer"])
            await award_points_for_action(user_id, "search")
            await gsheets_client.add_interaction_to_sheet(
                config.QUESTIONS_SHEET_NAME,
                [
                    user_id,
                    question,
                    json_result["answer"],
                    json_result["score"],
                    json_result["category"],
                    "N/A",
                    "N/A",
                    "Search (JSON)",
                    f"JSON search result for {question}",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
            )
            end = time.time()
            return f"📚 *{sanitize_markdown(get_translated_text('json_result', lang).format(category=json_result['category']))}*\n\n{sanitize_markdown(json_result['answer'])}\n\n🧠 *{sanitize_markdown(get_translated_text('similarity_score', lang))}*: {round(json_result['score']*100, 1)}%\n⏱️ *{sanitize_markdown(get_translated_text('response_time', lang))}*: {round(end - start, 2)} s"

        # 3. Documents
        doc_result = await search_in_documents(question)
        if doc_result:
            await redis_client.cache_answer(question, doc_result)
            await award_points_for_action(user_id, "search")
            await gsheets_client.add_interaction_to_sheet(
                config.QUESTIONS_SHEET_NAME,
                [
                    user_id,
                    question,
                    doc_result[:1000],
                    0,
                    "Documents",
                    "N/A",
                    "N/A",
                    "Search (Documents)",
                    f"Document search result for {question}",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
            )
            end = time.time()
            return f"📄 *{sanitize_markdown(get_translated_text('doc_result', lang))}*\n\n{sanitize_markdown(doc_result)}\n\n⏱️ *{sanitize_markdown(get_translated_text('response_time', lang))}*: {round(end - start, 2)} s"

        # 4. GPT (fallback)
        gpt_result = await ask_gpt(question)
        if gpt_result:
            await redis_client.cache_answer(question, gpt_result)
            await award_points_for_action(user_id, "search")
            await gsheets_client.add_interaction_to_sheet(
                config.QUESTIONS_SHEET_NAME,
                [
                    user_id,
                    question,
                    gpt_result[:1000],
                    0,
                    "GPT",
                    "N/A",
                    "N/A",
                    "Search (GPT)",
                    f"GPT search result for {question}",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
            )
            end = time.time()
            return f"🤖 *{sanitize_markdown(get_translated_text('gpt_result', lang))}*\n\n{sanitize_markdown(gpt_result)}\n\n⏱️ *{sanitize_markdown(get_translated_text('response_time', lang))}*: {round(end - start, 2)} s"

        # 5. Notify admin
        await notify_admin_unanswered(question, user_id)
        end = time.time()
        return f"❗ *{sanitize_markdown(get_translated_text('no_answer_found', lang))}*\n\n{sanitize_markdown(get_translated_text('admin_will_reply', lang))}\n\n⏱️ *{sanitize_markdown(get_translated_text('response_time', lang))}*: {round(end - start, 2)} s"

    except Exception as e:
        logger.error(f"❌ Unexpected error in smart_search for user {user_id}: {str(e)}")
        return f"😕 *{sanitize_markdown(get_translated_text('error_occurred', lang))}*\n\n⏱️ *{sanitize_markdown(get_translated_text('response_time', lang))}*: {round(time.time() - start, 2)} s"

def get_ai_utils_handler():
    """Return the AI utils handler (for reference, not a Telegram handler)."""
    return None
