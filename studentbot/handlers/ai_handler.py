import logging
import os
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from telegram.error import TelegramError
from gtts import gTTS
from studentbot import config
from studentbot.utils.common import get_translated_text, sanitize_markdown  # Changed from text_formatter
from studentbot.utils.redis_utils import redis_client
from studentbot.utils.ai_utils import smart_search
from studentbot.utils.db_utils import get_user, log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot.utils.ai_models import AIModels
from datetime import datetime

logger = logging.getLogger(__name__)

async def ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompt user to ask a question."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("ask_prompt", lang)),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ User {user_id} prompted to ask a question")
    except TelegramError as e:
        logger.error(f"❌ Telegram error prompting user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user question and provide an answer."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    question = update.message.text.strip()
    
    try:
        answer = await smart_search(question, user_id, lang)
        
        user = await get_user(user_id)
        if user:
            interaction_data = [
                user_id,
                user.first_name,
                user.last_name or "N/A",
                user.age or 0,
                user.email or "N/A",
                user.field_of_study or "N/A",
                user.country or "N/A",
                question,
                answer[:1000],
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            ]
            await gsheets_client.add_row_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data, "question")
        
        await award_points_for_action(user_id, "interaction")
        await log_event(user_id, "question_answered", f"Question: {question}, Answer: {answer[:1000]}")
        
        keyboard = [
            [InlineKeyboardButton(get_translated_text("tts_button", lang), callback_data=f"tts_{answer[:1000]}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            sanitize_markdown(answer),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        logger.info(f"✅ Answered question for user {user_id}: {question}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error answering question for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error answering question for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def text_to_speech(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Convert text to speech and send as voice message."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    text = " ".join(context.args).strip()
    
    if not text:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("tts_prompt", lang)),
            parse_mode="MarkdownV2"
        )
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
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error generating TTS for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
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
        
        stt_pipeline = AIModels().get_stt_pipeline()
        text = stt_pipeline(file_path)["text"]
        os.remove(file_path)
        
        keyboard = [
            [
                InlineKeyboardButton(get_translated_text("yes", lang), callback_data=f"stt_yes_{text[:1000]}"),
                InlineKeyboardButton(get_translated_text("no", lang), callback_data="stt_no"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("stt_confirm_prompt", lang).format(text=sanitize_markdown(text))),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup,
        )
        await award_points_for_action(user_id, "stt")
        await log_event(user_id, "stt_processed", f"Text: {text}")
        logger.info(f"✅ Processed STT for user {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error processing STT for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error processing STT for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
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
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("searching", lang)),
                parse_mode="MarkdownV2"
            )
            answer = await smart_search(text, user_id, lang)
            
            user = await get_user(user_id)
            if user:
                interaction_data = [
                    user_id,
                    user.first_name,
                    user.last_name or "N/A",
                    user.age or 0,
                    user.email or "N/A",
                    user.field_of_study or "N/A",
                    user.country or "N/A",
                    text,
                    answer[:1000],
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                ]
                await gsheets_client.add_row_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data, "question")
            
            await award_points_for_action(user_id, "interaction")
            await log_event(user_id, "stt_confirmed", f"Text: {text}, Answer: {answer[:1000]}")
            await query.edit_message_text(
                sanitize_markdown(answer),
                parse_mode="MarkdownV2"
            )
        else:
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("stt_cancelled", lang)),
                parse_mode="MarkdownV2"
            )
            await log_event(user_id, "stt_cancelled", "User cancelled STT")
        logger.info(f"✅ Handled STT callback for user {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error in STT callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error in STT callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

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
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error in TTS callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
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
