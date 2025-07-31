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
from config import config
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import create_consultation_request, get_consultation_requests, log_event, update_consultation_request_status
from studentbot.utils.gdrive import gdrive_client
from studentbot.utils.gsheets import gsheets_client
from studentbot.gamification_handler import award_points_for_action

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
        await update.message.reply_text(get_translated_text(prompt_key, lang))
        return next_state
    except TelegramError as e:
        logger.error(f"❌ Telegram error sending prompt to user {update.effective_user.id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
        return ConversationHandler.END

async def start_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the consultation process."""
    user_id = update.effective_user.id
    logger.info(f"Consultation started by user {user_id}")
    return await prompt(update, context, "consultation_name_prompt", NAME)

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle name input."""
    lang = context.user_data.get("lang", "en")
    name = update.message.text.strip()
    if not name:
        await update.message.reply_text(get_translated_text("invalid_name", lang))
        return NAME
    context.user_data["consultation_name"] = name
    logger.info(f"Name received for user {update.effective_user.id}: {name}")
    return await prompt(update, context, "consultation_field_of_study_prompt", FIELD_OF_STUDY)

async def field_of_study(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle field of study input."""
    lang = context.user_data.get("lang", "en")
    field = update.message.text.strip()
    if not field:
        await update.message.reply_text(get_translated_text("invalid_field_of_study", lang))
        return FIELD_OF_STUDY
    context.user_data["consultation_field_of_study"] = field
    return await prompt(update, context, "consultation_level_prompt", LEVEL)

async def level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle academic level input."""
    lang = context.user_data.get("lang", "en")
    level = update.message.text.strip()
    if not await validate_level(level):
        await update.message.reply_text(get_translated_text("invalid_level", lang))
        return LEVEL
    context.user_data["consultation_level"] = level
    return await prompt(update, context, "consultation_gpa_prompt", GPA)

async def gpa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle GPA input."""
    lang = context.user_data.get("lang", "en")
    gpa_text = update.message.text.strip()
    gpa = await validate_gpa(gpa_text)
    if gpa is None:
        await update.message.reply_text(get_translated_text("invalid_gpa", lang))
        return GPA
    context.user_data["consultation_gpa"] = gpa
    return await prompt(update, context, "consultation_destination_country_prompt", DESTINATION_COUNTRY)

async def destination_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle destination country input."""
    lang = context.user_data.get("lang", "en")
    country = update.message.text.strip()
    if not country:
        await update.message.reply_text(get_translated_text("invalid_country", lang))
        return DESTINATION_COUNTRY
    context.user_data["consultation_destination_country"] = country
    return await prompt(update, context, "consultation_language_level_prompt", LANGUAGE_LEVEL)

async def language_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle language level input."""
    lang = context.user_data.get("lang", "en")
    lang_level = update.message.text.strip()
    if not await validate_language_level(lang_level):
        await update.message.reply_text(get_translated_text("invalid_language_level", lang))
        return LANGUAGE_LEVEL
    context.user_data["consultation_language_level"] = lang_level
    return await prompt(update, context, "consultation_budget_prompt", BUDGET)

async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle budget input."""
    lang = context.user_data.get("lang", "en")
    budget = update.message.text.strip()
    if not await validate_budget(budget):
        await update.message.reply_text(get_translated_text("invalid_budget", lang))
        return BUDGET
    context.user_data["consultation_budget"] = budget
    return await prompt(update, context, "consultation_work_experience_prompt", WORK_EXPERIENCE)

async def work_experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle work experience input."""
    lang = context.user_data.get("lang", "en")
    context.user_data["consultation_work_experience"] = update.message.text.strip()
    return await prompt(update, context, "consultation_special_needs_prompt", SPECIAL_NEEDS)

async def special_needs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle special needs input."""
    lang = context.user_data.get("lang", "en")
    context.user_data["consultation_special_needs"] = update.message.text.strip()
    return await prompt(update, context, "consultation_upload_resume_prompt", UPLOAD_RESUME)

async def upload_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle resume upload and complete consultation request."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    try:
        document = update.message.document
        if not document:
            await update.message.reply_text(get_translated_text("no_document_received", lang))
            return UPLOAD_RESUME
        
        # Validate file format and size
        if not await validate_file(document):
            allowed = ", ".join([".pdf", ".doc", ".docx"])
            max_size = 10
            if document.file_size > 10 * 1024 * 1024:
                await update.message.reply_text(
                    get_translated_text("file_too_large", lang).format(max_size=max_size)
                )
            else:
                await update.message.reply_text(
                    get_translated_text("invalid_file_format", lang).format(allowed=allowed)
                )
            return UPLOAD_RESUME
        
        # Download file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=document.file_name) as tmp_file:
            file_path = tmp_file.name
            file = await context.bot.get_file(document.file_id)
            await file.download_to_drive(file_path)
            logger.info(f"Resume received from user {user_id}, saved as {file_path}")
            
            # Upload to Google Drive
            file_id = await gdrive_client.upload_file(file_path, user_id, document.file_name)
        
        # Remove temporary file
        try:
            os.unlink(file_path)
            logger.info(f"File {file_path} removed from local storage")
        except Exception as e:
            logger.warning(f"⚠️ Failed to remove temporary file {file_path}: {str(e)}")
        
        # Save to database
        data = context.user_data
        await create_consultation_request(
            user_id=user_id,
            name=data["consultation_name"],
            field_of_study=data["consultation_field_of_study"],
            level=data["consultation_level"],
            gpa=data["consultation_gpa"],
            destination_country=data["consultation_destination_country"],
            language_level=data["consultation_language_level"],
            budget=data["consultation_budget"],
            work_experience=data["consultation_work_experience"],
            special_needs=data["consultation_special_needs"],
            status="pending",
            file_id=file_id,
        )
        
        # Save to Google Sheets
        user = await get_user(user_id)  # Assumes get_user is defined in db_utils
        if user:
            consultation_data = [
                user_id,
                user["first_name"],
                user["last_name"],
                user["age"],
                user["email"],
                data["consultation_field_of_study"],
                data["consultation_destination_country"],
                data["consultation_name"],
                f"Resume uploaded: {file_id}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            ]
            await gsheets_client.add_consultation_to_sheet(config.QUESTIONS_SHEET_NAME, consultation_data)
        
        # Award gamification points
        await award_points_for_action(user_id, "consultation")
        await award_points_for_action(user_id, "file_upload")
        await log_event(user_id, "consultation_submitted", f"File ID: {file_id}")
        
        # Notify admin
        if config.ADMIN_CHAT_ID:
            try:
                admin_message = f"""🆕 *New Consultation Request*
*Name:* {sanitize_markdown(data["consultation_name"])}
*Field of Study:* {sanitize_markdown(data["consultation_field_of_study"])}
*Destination Country:* {sanitize_markdown(data["consultation_destination_country"])}
*File ID:* {file_id}
*Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"""
                if len(admin_message) > 4096:
                    admin_message = admin_message[:4000] + "..."
                keyboard = [
                    [
                        InlineKeyboardButton(
                            get_translated_text("respond_button", "en"),
                            callback_data=f"respond_consult_{user_id}"
                        ),
                        InlineKeyboardButton(
                            get_translated_text("archive_button", "en"),
                            callback_data=f"archive_consult_{user_id}"
                        ),
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(
                    chat_id=config.ADMIN_CHAT_ID,
                    text=admin_message,
                    parse_mode="MarkdownV2",
                    reply_markup=reply_markup,
                )
            except TelegramError as e:
                logger.error(f"❌ Telegram error notifying admin for user {user_id}: {str(e)}")
        
        await update.message.reply_text(get_translated_text("consultation_complete", lang))
        context.user_data.clear()
        context.user_data["lang"] = lang  # Preserve language
        logger.info(f"✅ Consultation request completed for user {user_id}")
        return ConversationHandler.END
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error in upload_resume for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Unexpected error in upload_resume for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
        return ConversationHandler.END

async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin actions from inline buttons."""
    query = update.callback_query
    await query.answer()
    
    lang = context.user_data.get("lang", "en")
    try:
        user_id = int(query.data.split("_")[-1])
        action = query.data.split("_")[0]
        
        if action == "respond":
            await update_consultation_request_status(user_id, "responded")
            await query.message.reply_text(get_translated_text("consultation_responded", lang))
        elif action == "archive":
            await update_consultation_request_status(user_id, "archived")
            await query.message.reply_text(get_translated_text("consultation_archived", lang))
        logger.info(f"✅ Admin action '{action}' performed for consultation of user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error performing admin action '{action}' for user {user_id}: {str(e)}")
        await query.message.reply_text(get_translated_text("error_occurred", lang))

async def cancel_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the consultation process."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    try:
        await update.message.reply_text(get_translated_text("consultation_cancelled", lang))
        context.user_data.clear()
        context.user_data["lang"] = lang  # Preserve language
        logger.info(f"✅ Consultation cancelled by user {user_id}")
        return ConversationHandler.END
    except TelegramError as e:
        logger.error(f"❌ Telegram error cancelling consultation for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
        return ConversationHandler.END

async def consult_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the status of a user's consultation requests."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    
    try:
        requests = await get_consultation_requests(user_id)
        if not requests:
            await update.message.reply_text(get_translated_text("no_consultation_requests", lang))
            return
        
        for req in requests:
            message = f"""*Request ID:* {req['id']}
*Status:* {sanitize_markdown(req['status'])}
*Field of Study:* {sanitize_markdown(req['field_of_study'])}
*Destination Country:* {sanitize_markdown(req['destination_country'])}
*File ID:* {req.get('file_id', 'N/A')}
*Created At:* {req['created_at'].strftime('%Y-%m-%d %H:%M:%S')}"""
            if len(message) > 4096:
                message = message[:4000] + "..."
            await update.message.reply_text(message, parse_mode="MarkdownV2")
        logger.info(f"✅ Consultation status shown for user {user_id}")
    except TelegramError as e:
        logger.error(f"❌ Telegram error retrieving consultation status for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
    except Exception as e:
        logger.error(f"❌ Unexpected error retrieving consultation status for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))

def get_consultation_handler():
    """Return the consultation handlers."""
    return [
        ConversationHandler(
            entry_points=[CommandHandler("consult", start_consultation)],
            states={
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
                FIELD_OF_STUDY: [MessageHandler(filters.TEXT & ~filters.COMMAND, field_of_study)],
                LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, level)],
                GPA: [MessageHandler(filters.TEXT & ~filters.COMMAND, gpa)],
                DESTINATION_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, destination_country)],
                LANGUAGE_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, language_level)],
                BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, budget)],
                WORK_EXPERIENCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, work_experience)],
                SPECIAL_NEEDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, special_needs)],
                UPLOAD_RESUME: [MessageHandler(filters.Document.ALL & ~filters.COMMAND, upload_resume)],
            },
            fallbacks=[
                CommandHandler("cancel", cancel_consultation),
                CallbackQueryHandler(handle_admin_action, pattern="^(respond_consult|archive_consult)_"),
            ],
        ),
        CommandHandler("consult_status", consult_status),
    ]
