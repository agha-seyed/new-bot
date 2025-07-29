import os
import json
import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.error import TelegramError
from transformers import pipeline
from gtts import gTTS
from sentence_transformers import SentenceTransformer, util
from config import config
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.redis_utils import get_cached_answer, cache_answer
from studentbot.utils.ai_utils import smart_search
from studentbot.utils.db_utils import log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.gamification_handler import award_points_for_action
from datetime import datetime

logger = logging.getLogger(__name__)

# Load models with lazy initialization to save memory
model = None
qa_pipeline = None
tts_pipeline = None
stt_pipeline = None

def initialize_models():
    """Initialize AI models with error handling."""
    global model, qa_pipeline, tts_pipeline, stt_pipeline
    try:
        model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
        qa_pipeline = pipeline(
            "question-answering",
            model="distilbert-base-cased-distilled-squad",
            tokenizer="distilbert-base-cased-distilled-squad",
        )
        # Use gTTS instead of heavy tts_pipeline for memory efficiency
        # tts_pipeline = pipeline("text-to-speech", model="espnet/kan-bayashi_ljspeech_vits")
        stt_pipeline = pipeline("automatic-speech-recognition", model="openai/whisper-tiny")  # Lighter model
        logger.info("✅ AI models initialized successfully")
    except Exception as e:
        logger.error(f"❌ Error initializing AI models: {str(e)}")
        raise

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompt user to ask a question."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    try:
        await update.message.reply_text(get_translated_text("ask_prompt", lang))
        logger.info(f"✅ User {user_id} prompted to ask a question")
    except TelegramError as e:
        logger.error(f"❌ Telegram error prompting user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user question and provide an answer."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    question = update.message.text.strip()
    
    try:
        # Check cache
        cached_answer = await get_cached_answer(question)
        if cached_answer:
            await update.message.reply_text(cached_answer.decode("utf-8"))
            await log_event(user_id, "question_answered", f"Cached answer for: {question}")
            logger.info(f"✅ Served cached answer for user {user_id}: {question}")
            return
        
        # Load QnA data
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        qna_file_path = os.path.join(base_dir, "qna.json")
        try:
            with open(qna_file_path, "r", encoding="utf-8") as f:
                qna_data = json.load(f)
        except FileNotFoundError:
            logger.error(f"❌ QnA file not found: {qna_file_path}")
            await update.message.reply_text(get_translated_text("error_occurred", lang))
            return
        except json.JSONDecodeError:
            logger.error(f"❌ Invalid QnA file format: {qna_file_path}")
            await update.message.reply_text(get_translated_text("error_occurred", lang))
            return
        
        # Find best match
        questions = [q["q"] for q in qna_data["questions"]]
        if not model:
            initialize_models()
        
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
            await cache_answer(question, answer)
        else:
            answer = await smart_search(question, user_id)
        
        # Store interaction in Google Sheets
        user = await db_utils.get_user(user_id)
        if user:
            interaction_data = [
                user_id,
                user["first_name"],
                user["last_name"],
                user["age"],
                user["email"],
                user.get("field_of_study", "N/A"),
                user.get("country", "N/A"),
                question,
                answer,
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            ]
            await gsheets_client.add_consultation_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        # Award points
        await award_points_for_action(user_id, "interaction")
        await log_event(user_id, "question_answered", f"Question: {question}, Answer: {answer}")
        
        # Send response with TTS button
        keyboard = [
            [InlineKeyboardButton(get_translated_text("tts_button", lang), callback_data=f"tts_{answer}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(sanitize_markdown(answer), parse_mode="MarkdownV2", reply_markup=reply_markup)
        logger.info(f"✅ Answered question for user {user_id}: {question}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error answering question for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error answering question for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))

async def text_to_speech(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert text to speech and send as voice message."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    text = " ".join(context.args).strip()
    
    if not text:
        await update.message.reply_text(get_translated_text("tts_prompt", lang))
        return
    
    try:
        tts = gTTS(text, lang=lang)
        file_path = f"tts_{user_id}.mp3"
        tts.save(file_path)
        with open(file_path, "rb") as voice_file:
            await context.bot.send_voice(chat_id=update.effective_chat.id, voice=voice_file)
        os.remove(file_path)
        await award_points_for_action(user_id, "tts")
        await log_event(user_id, "tts_generated", f"Text: {text}")
        logger.info(f"✅ Generated TTS for user {user_id}")
    except TelegramError as e:
        logger.error(f"❌ Telegram error sending TTS for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error generating TTS for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
        if os.path.exists(file_path):
            os.remove(file_path)

async def speech_to_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert voice to text and confirm with user."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    voice = update.message.voice
    
    try:
        file = await context.bot.get_file(voice.file_id)
        file_path = f"stt_{user_id}.ogg"
        await file.download_to_drive(file_path)
        
        if not stt_pipeline:
            initialize_models()
        
        text = stt_pipeline(file_path)["text"]
        os.remove(file_path)
        
        keyboard = [
            [
                InlineKeyboardButton(get_translated_text("yes", lang), callback_data=f"stt_yes_{text}"),
                InlineKeyboardButton(get_translated_text("no", lang), callback_data="stt_no"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            get_translated_text("stt_confirm_prompt", lang).format(text=sanitize_markdown(text)),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup,
        )
        await award_points_for_action(user_id, "stt")
        await log_event(user_id, "stt_processed", f"Text: {text}")
        logger.info(f"✅ Processed STT for user {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error processing STT for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error processing STT for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
        if os.path.exists(file_path):
            os.remove(file_path)

async def stt_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle STT confirmation callback."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "en")
    user_id = query.from_user.id
    
    try:
        data = query.data.split("_", 2)
        if data[1] == "yes":
            text = data[2]
            await query.edit_message_text(text=get_translated_text("searching", lang))
            answer = await smart_search(text, user_id)
            
            # Store interaction in Google Sheets
            user = await db_utils.get_user(user_id)
            if user:
                interaction_data = [
                    user_id,
                    user["first_name"],
                    user["last_name"],
                    user["age"],
                    user["email"],
                    user.get("field_of_study", "N/A"),
                    user.get("country", "N/A"),
                    text,
                    answer,
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                ]
                await gsheets_client.add_consultation_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
            
            await award_points_for_action(user_id, "interaction")
            await log_event(user_id, "stt_confirmed", f"Text: {text}, Answer: {answer}")
            await query.edit_message_text(text=sanitize_markdown(answer), parse_mode="MarkdownV2")
        else:
            await query.edit_message_text(text=get_translated_text("stt_cancelled", lang))
            await log_event(user_id, "stt_cancelled", "User cancelled STT")
        logger.info(f"✅ Handled STT callback for user {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error in STT callback for user {user_id}: {str(e)}")
        await query.edit_message_text(text=get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error in STT callback for user {user_id}: {str(e)}")
        await query.edit_message_text(text=get_translated_text("error_occurred", lang))

async def tts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle TTS callback."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "en")
    user_id = query.from_user.id
    text = query.data.split("_", 1)[1]
    
    try:
        tts = gTTS(text, lang=lang)
        file_path = f"tts_{user_id}.mp3"
        tts.save(file_path)
        with open(file_path, "rb") as voice_file:
            await context.bot.send_voice(chat_id=update.effective_chat.id, voice=voice_file)
        os.remove(file_path)
        await award_points_for_action(user_id, "tts")
        await log_event(user_id, "tts_generated", f"Text: {text}")
        logger.info(f"✅ Generated TTS for user {user_id} from callback")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error in TTS callback for user {user_id}: {str(e)}")
        await query.edit_message_text(text=get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error in TTS callback for user {user_id}: {str(e)}")
        await query.edit_message_text(text=get_translated_text("error_occurred", lang))
        if os.path.exists(file_path):
            os.remove(file_path)

def get_ai_handler():
    """Return the AI handlers."""
    return [
        CommandHandler("ask", ask),
        MessageHandler(filters.TEXT & ~filters.COMMAND, answer),
        CommandHandler("tts", text_to_speech),
        MessageHandler(filters.VOICE, speech_to_text),
        CallbackQueryHandler(tts_callback, pattern="^tts_"),
        CallbackQueryHandler(stt_callback, pattern="^stt_"),
    ]