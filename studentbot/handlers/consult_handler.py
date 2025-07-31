import logging
import os
from typing import Optional
from datetime import datetime
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.error import TelegramError
from studentbot import config
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import create_consultation_request, get_consultation_requests, log_event, update_consultation_request_status, get_user
from studentbot.utils.gdrive import gdrive_client
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action

logger = logging.getLogger(__name__)

# States for the conversation
(
    NAME,
    FIELD_OF_STUDY,
    LEVEL,
    GPA,
    DESTINATION_COUNTRY,
    LANGUAGE_LEVEL,
    BUDGET,
    WORK_EXPERIENCE,
    SPECIAL_NEEDS,
    UPLOAD_RESUME,
) = range(10)

async def validate_gpa(gpa_text: str) -> Optional[float]:
    """Validate GPA input (between 0 and 20)."""
    try:
        gpa = float(gpa_text)
        if not 0 <= gpa <= 20:
            raise ValueError("GPA must be between 0 and 20.")
        return gpa
    except ValueError:
        return None

async def validate_level(level: str) -> bool:
    """Validate academic level input."""
    valid_levels = ["Bachelor", "Master", "PhD", "Other"]
    return level.strip() in valid_levels

async def validate_language_level(lang_level: str) -> bool:
    """Validate language proficiency level input."""
    valid_levels = ["A1", "A2", "B1", "B2", "C1", "C2"]
    return lang_level.strip() in valid_levels

async def validate_budget(budget: str) -> bool:
    """Validate budget input (number or number with currency)."""
    try:
        budget_clean = budget.strip().split()[0]
        float(budget_clean)
        return True
    except ValueError:
        return False

async def validate_file(document: 'telegram.Document') -> bool:
    """Validate uploaded file (size and format)."""
    max_size = 10 * 1024 * 1024  # 10MB
    allowed_extensions = (".pdf", ".doc", ".docx")
    if document.file_size > max_size:
        return False
    return document.file_name.lower().endswith(allowed_extensions)

async def prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt_key: str, next_state: int) -> int:
    """Send a translated prompt to the user and return the next state."""
    lang = context.user_data.get("lang", "en")
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text(prompt_key, lang)),
            parse_mode="MarkdownV2"
        )
        return next_state
    except TelegramError as e:
        logger.error(f"❌ Telegram error sending prompt to user {update.effective_user.id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def start_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the consultation process."""
    user_id = update.effective_user.id
    logger.info(f"🗣️ Consultation started by user {user_id}")
    return await prompt(update, context, "consultation_name_prompt", NAME)

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle name input."""
    lang = context.user_data.get("lang", "en")
    name = update.message.text.strip()
    if not name or len(name) < 2:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_name", lang)),
            parse_mode="MarkdownV2"
        )
        return NAME
    context.user_data["consultation_name"] = name
    logger.info(f"👤 Name received for user {update.effective_user.id}: {name}")
    return await prompt(update, context, "consultation_field_of_study_prompt", FIELD_OF_STUDY)

async def field_of_study(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle field of study input."""
    lang = context.user_data.get("lang", "en")
    field = update.message.text.strip()
    if not field or len(field) < 3:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_field_of_study", lang)),
            parse_mode="MarkdownV2"
        )
        return FIELD_OF_STUDY
    context.user_data["consultation_field_of_study"] = field
    return await prompt(update, context, "consultation_level_prompt", LEVEL)

async def level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle academic level input."""
    lang = context.user_data.get("lang", "en")
    level = update.message.text.strip()
    if not await validate_level(level):
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_level", lang)),
            parse_mode="MarkdownV2"
        )
        return LEVEL
    context.user_data["consultation_level"] = level
    return await prompt(update, context, "consultation_gpa_prompt", GPA)

async def gpa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle GPA input."""
    lang = context.user_data.get("lang", "en")
    gpa_text = update.message.text.strip()
    gpa = await validate_gpa(gpa_text)
    if gpa is None:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_gpa", lang)),
            parse_mode="MarkdownV2"
        )
        return GPA
    context.user_data["consultation_gpa"] = gpa
    return await prompt(update, context, "consultation_destination_country_prompt", DESTINATION_COUNTRY)

async def destination_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle destination country input."""
    lang = context.user_data.get("lang", "en")
    country = update.message.text.strip()
    if not country or len(country) < 2:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_country", lang)),
            parse_mode="MarkdownV2"
        )
        return DESTINATION_COUNTRY
    context.user_data["consultation_destination_country"] = country
    return await prompt(update, context, "consultation_language_level_prompt", LANGUAGE_LEVEL)

async def language_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language level input."""
    lang = context.user_data.get("lang", "en")
    lang_level = update.message.text.strip()
    if not await validate_language_level(lang_level):
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_language_level", lang)),
            parse_mode="MarkdownV2"
        )
        return LANGUAGE_LEVEL
    context.user_data["consultation_language_level"] = lang_level
    return await prompt(update, context, "consultation_budget_prompt", BUDGET)

async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle budget input."""
    lang = context.user_data.get("lang", "en")
    budget = update.message.text.strip()
    if not await validate_budget(budget):
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_budget", lang)),
            parse_mode="MarkdownV2"
        )
        return BUDGET
    context.user_data["consultation_budget"] = budget
    return await prompt(update, context, "consultation_work_experience_prompt", WORK_EXPERIENCE)

async def work_experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle work experience input."""
    lang = context.user_data.get("lang", "en")
    work_exp = update.message.text.strip()
    context.user_data["consultation_work_experience"] = work_exp if work_exp else "N/A"
    return await prompt(update, context, "consultation_special_needs_prompt", SPECIAL_NEEDS)

async def special_needs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle special needs input."""
    lang = context.user_data.get("lang", "en")
    special_needs = update.message.text.strip()
    context.user_data["consultation_special_needs"] = special_needs if special_needs else "N/A"
    return await prompt(update, context, "consultation_upload_resume_prompt", UPLOAD_RESUME)

async def upload_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle resume upload and complete consultation request."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    try:
        document = update.message.document
        if not document:
            await update.message.reply_text(
                sanitize_markdown(get_translated_text("no_document_received", lang)),
                parse_mode="MarkdownV2"
            )
            return UPLOAD_RESUME
        
        if not await validate_file(document):
            allowed = ", ".join([".pdf", ".doc", ".docx"])
            max_size = 10
            if document.file_size > 10 * 1024 * 1024:
                await update.message.reply_text(
                    sanitize_markdown(get_translated_text("file_too_large", lang).format(max_size=max_size)),
                    parse_mode="MarkdownV2"
                )
            else:
                await update.message.reply_text(
                    sanitize_markdown(get_translated_text("invalid_file_format", lang).format(allowed=allowed)),
                    parse_mode="MarkdownV2"
                )
            return UPLOAD_RESUME
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=document.file_name) as tmp_file:
            file_path = tmp_file.name
            file = await context.bot.get_file(document.file_id)
           
