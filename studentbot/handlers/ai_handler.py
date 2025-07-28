import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from transformers import pipeline
from gtts import gTTS
from sentence_transformers import SentenceTransformer, util

from utils.text_formatter import get_translated_text
from utils.redis_utils import get_cached_answer, cache_answer
from utils.ai_utils import smart_search

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

    # Check for cached answer
    cached_answer = get_cached_answer(question)
    if cached_answer:
        await update.message.reply_text(cached_answer.decode("utf-8"))
        return

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
        cache_answer(question, answer)
    else:
        answer = "I'm sorry, I don't have an answer to that question."

    keyboard = [
        [
            InlineKeyboardButton(
                get_translated_text("tts_button", lang), callback_data=f"tts_{answer}"
            )
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(answer, reply_markup=reply_markup)


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

    # Ask for confirmation
    keyboard = [
        [
            InlineKeyboardButton(get_translated_text("yes", lang), callback_data=f"stt_yes_{text}"),
            InlineKeyboardButton(get_translated_text("no", lang), callback_data="stt_no"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        get_translated_text("stt_confirm_prompt", lang).format(text=text),
        reply_markup=reply_markup,
    )
    os.remove(file_path)


async def stt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the STT callback."""
    query = update.callback_query
    await query.answer()
    data = query.data.split("_", 2)
    if data[1] == "yes":
        text = data[2]
        user_id = query.from_user.id
        await query.edit_message_text(text=get_translated_text("searching", "en"))
        answer = await smart_search(text, user_id)
        await query.edit_message_text(text=answer)
    else:
        await query.edit_message_text(text=get_translated_text("stt_cancelled", "en"))


async def tts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the TTS callback."""
    query = update.callback_query
    await query.answer()
    text = query.data.split("_", 1)[1]
    lang = context.user_data.get("lang", "en")
    tts = gTTS(text, lang=lang)
    tts.save("tts.mp3")
    await context.bot.send_voice(chat_id=update.effective_chat.id, voice=open("tts.mp3", "rb"))
    os.remove("tts.mp3")

def get_ai_handler():
    """Returns the AI handler."""
    return [
        CommandHandler("ask", ask),
        MessageHandler(filters.TEXT & ~filters.COMMAND, answer),
        CommandHandler("tts", text_to_speech),
        MessageHandler(filters.VOICE, speech_to_text),
        CallbackQueryHandler(tts_callback, pattern="^tts_"),
        CallbackQueryHandler(stt_callback, pattern="^stt_"),
    ]
