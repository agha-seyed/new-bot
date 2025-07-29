import os
import json
import time
import logging
import asyncio

from sentence_transformers import util
from transformers import pipeline

from studentbot.handlers.ai_handler import model
from studentbot.utils.text_extractor import search_in_documents
from studentbot.utils.redis_utils import get_cached_answer, cache_answer
from studentbot.utils.alert_admin import notify_admin_unanswered
from studentbot.utils.gsheets import log_search_result
from studentbot.utils.text_formatter import get_translated_text


logger = logging.getLogger(name)

def search_in_json(question, lang="fa"): """Searches for an answer in the local JSON knowledge base.""" base_dir = os.path.dirname(os.path.dirname(os.path.abspath(file))) qna_file_path = os.path.join(base_dir, "qna.json") with open(qna_file_path, "r", encoding="utf-8") as f: qna_data = json.load(f)

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

logger.info(f"Question: {question}, Best match score: {best_match_score}")

if best_match_score > 0.7:
    answer_entry = qna_data["questions"][best_match_index]
    answer = answer_entry["a"].get(lang, answer_entry["a"].get("fa", ""))
    category = answer_entry.get("category", "عمومی")
    return {
        "answer": answer,
        "source": "json",
        "score": best_match_score,
        "category": category
    }
return None

def ask_huggingface(question): """Asks a question to the Hugging Face QA pipeline.""" qa_pipeline = pipeline( "question-answering", model="distilbert-base-cased-distilled-squad", tokenizer="distilbert-base-cased-distilled-squad", ) context = "The Student Helper Bot is a Telegram bot designed to help international students, especially in Perugia." result = qa_pipeline(question=question, context=context) return { "answer": result["answer"], "source": "huggingface", "score": result["score"] }

def smart_search(question, user_id, lang="fa"): """Performs a smart search for a user's question.""" start = time.time()

# 1. Try cache first
cached = get_cached_answer(question)
if cached:
    return f"📦 *پاسخ قبلی شما (از حافظه):*

{cached}"

# 2. JSON Knowledge Base
json_result = search_in_json(question, lang)
if json_result:
    cache_answer(question, json_result["answer"])
    save_search_log(user_id, question, json_result["answer"], "JSON", json_result["score"])
    end = time.time()
    return f"📚 *پاسخ از پایگاه دانش ({json_result['category']})*

{json_result['answer']}

🧠 شباهت: {round(json_result['score']*100, 1)}٪ ⏱️ زمان پاسخگویی: {round(end - start, 2)} ثانیه"

# 3. Documents
doc_result = search_in_documents(question)
if doc_result:
    cache_answer(question, doc_result)
    save_search_log(user_id, question, doc_result, "docs")
    end = time.time()
    return f"📄 *پاسخ از فایل‌ها:*

{doc_result}

⏱️ زمان پاسخگویی: {round(end - start, 2)} ثانیه"

# 4. AI Model (fallback)
ai_result = ask_huggingface(question)
if ai_result:
    cache_answer(question, ai_result["answer"])
    save_search_log(user_id, question, ai_result["answer"], "huggingface", ai_result["score"])
    end = time.time()
    return f"🤖 *پاسخ هوش مصنوعی:*

{ai_result['answer']}

🧠 اطمینان مدل: {round(ai_result['score']*100, 1)}٪ ⏱️ زمان پاسخگویی: {round(end - start, 2)} ثانیه"

# 5. Notify admin
asyncio.create_task(notify_admin_unanswered(question, user_id))
end = time.time()
return f"❗ متأسفم، پاسخی پیدا نکردم.

سؤال شما برای ادمین ارسال شد. ⏱️ زمان بررسی: {round(end - start, 2)} ثانیه"

