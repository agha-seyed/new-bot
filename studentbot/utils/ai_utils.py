import json
from sentence_transformers import util

from studentbot.handlers.ai_handler import model
from studentbot.utils.text_extractor import search_in_documents
from studentbot.utils.redis_utils import get_cached_answer, cache_answer
from studentbot.utils.alert_admin import notify_admin_unanswered


def search_in_json(question):
    """Searches for an answer in the knowledge base."""
    # Load the Q&A data
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    qna_file_path = os.path.join(base_dir, "qna.json")
    with open(qna_file_path, "r", encoding="utf-8") as f:
        qna_data = json.load(f)

    # Find the best match for the user's question
    questions = [q["q"] for q in qna_data["questions"]]
    question_embedding = model.encode(question, convert_to_tensor=True)
    best_match_score = 0
    best_match_index = -1
    for i, q in enumerate(questions):
        q_embedding = model.encode(q, convert_to_tensor=True)
        score = util.pytorch_cos_sim(question_embedding, q_embedding)
        if score > best_match_score:
            best_match_score = score
            best_match_index = i

    if best_match_score > 0.7:
        return qna_data["questions"][best_match_index]["a"]
    else:
        return None


def ask_huggingface(question):
    """Asks a question to the Hugging Face model."""
    # TODO: Implement this
    return None


def smart_search(question, user_id):
    """Performs a smart search for an answer."""
    # 1. Search in JSON
    json_result = search_in_json(question)
    if json_result:
        return json_result

    # 2. Search in documents
    doc_result = search_in_documents(question)
    if doc_result:
        return doc_result

    # 3. Use Hugging Face
    ai_result = ask_huggingface(question)
    if ai_result:
        return ai_result

    # 4. Notify admin
    notify_admin_unanswered(question, user_id)
    return "I'm sorry, I don't have an answer to that question. I have notified the admin about your question."
