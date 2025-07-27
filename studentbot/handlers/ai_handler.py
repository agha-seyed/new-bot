import os
from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters
from transformers import pipeline
from gtts import gTTS
from sentence_transformers import SentenceTransformer, util

from studentbot.utils.text_formatter import get_translated_text

# Load the sentence transformer model
model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

# Load the question answering pipeline
qa_pipeline = pipeline(
    "question-answering",
    model="distilbert-base-cased-distilled-squad",
    tokenizer="distilbert-base-cased-distilled-squad",
)

# Load the text to speech pipeline
tts_pipeline = pipeline("text-to-speech", model="espnet/kan-bayashi_ljspeech_vits")


async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Asks a question to the user."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("ask_prompt", lang))


import json

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Answers the user's question."""
    lang = context.user_data.get("lang", "en")
    question = update.message.text

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
        answer = qna_data["questions"][best_match_index]["a"]
    else:
        answer = "I'm sorry, I don't have an answer to that question."

    await update.message.reply_text(answer)


async def text_to_speech(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Converts text to speech."""
    lang = context.user_data.get("lang", "en")
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text(get_translated_text("tts_prompt", lang))
        return
    tts = gTTS(text, lang=lang)
    tts.save("tts.mp3")
    await context.bot.send_voice(chat_id=update.effective_chat.id, voice=open("tts.mp3", "rb"))
    os.remove("tts.mp3")


async def speech_to_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Converts speech to text."""
    lang = context.user_data.get("lang", "en")
    voice = update.message.voice
    file = await context.bot.get_file(voice.file_id)
    file_path = "stt.ogg"
    await file.download_to_drive(file_path)

    # Convert speech to text
    pipe = pipeline("automatic-speech-recognition", model="openai/whisper-small")
    text = pipe(file_path)["text"]

    await update.message.reply_text(text)
    os.remove(file_path)


def get_ai_handler():
    """Returns the AI handler."""
    return [
        CommandHandler("ask", ask),
        MessageHandler(filters.TEXT & ~filters.COMMAND, answer),
        CommandHandler("tts", text_to_speech),
        MessageHandler(filters.VOICE, speech_to_text),
    ]
