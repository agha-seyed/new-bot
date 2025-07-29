import os
import logging
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from studentbot.utils.text_formatter import get_translated_text
from studentbot.utils.db_utils import create_consultation_request, get_consultation_requests
from studentbot.utils.gdrive import upload_file

# === Logging setup ===
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# === States ===
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

# === Handlers ===

async def start_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    logger.info(f"Consultation started by user {update.message.from_user.id}")
    await update.message.reply_text(get_translated_text("consultation_name_prompt", lang))
    return NAME

async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["consultation_name"] = update.message.text
    lang = context.user_data.get("lang", "en")
    logger.info(f"Name received: {update.message.text}")
    await update.message.reply_text(get_translated_text("consultation_field_of_study_prompt", lang))
    return FIELD_OF_STUDY

async def field_of_study(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["consultation_field_of_study"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("consultation_level_prompt", lang))
    return LEVEL

async def level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["consultation_level"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("consultation_gpa_prompt", lang))
    return GPA

async def gpa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["consultation_gpa"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("consultation_destination_country_prompt", lang))
    return DESTINATION_COUNTRY

async def destination_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["consultation_destination_country"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("consultation_language_level_prompt", lang))
    return LANGUAGE_LEVEL

async def language_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["consultation_language_level"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("consultation_budget_prompt", lang))
    return BUDGET

async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["consultation_budget"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("consultation_work_experience_prompt", lang))
    return WORK_EXPERIENCE

async def work_experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["consultation_work_experience"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("consultation_special_needs_prompt", lang))
    return SPECIAL_NEEDS

async def special_needs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["consultation_special_needs"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("consultation_upload_resume_prompt", lang))
    return UPLOAD_RESUME

async def upload_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    user_id = update.message.from_user.id
    try:
        document = update.message.document
        file = await context.bot.get_file(document.file_id)
        file_path = f"{document.file_name}"
        await file.download_to_drive(file_path)
        logger.info(f"Resume received from user {user_id}, saved as {file_path}")

        upload_file(file_path, user_id, document.file_name)
        os.remove(file_path)

        data = context.user_data
        create_consultation_request(
            user_id,
            data["consultation_name"],
            data["consultation_field_of_study"],
            data["consultation_level"],
            data["consultation_gpa"],
            data["consultation_destination_country"],
            data["consultation_language_level"],
            data["consultation_budget"],
            data["consultation_work_experience"],
            data["consultation_special_needs"],
        )
        logger.info(f"Consultation request stored in DB for user {user_id}")

        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if admin_chat_id:
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=f"🆕 New consultation request from {data['consultation_name']}",
            )

        await update.message.reply_text(get_translated_text("consultation_complete", lang))
    except Exception as e:
        logger.error(f"❌ Error in upload_resume for user {user_id}: {e}")
        await update.message.reply_text(get_translated_text("consultation_error", lang))
    return ConversationHandler.END

async def cancel_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    logger.info(f"Consultation cancelled by user {update.message.from_user.id}")
    await update.message.reply_text(get_translated_text("consultation_cancelled", lang))
    return ConversationHandler.END

async def consult_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "en")
    user_id = update.message.from_user.id
    try:
        requests = get_consultation_requests(user_id)
        if not requests:
            await update.message.reply_text(get_translated_text("no_consultation_requests", lang))
            return

        for req in requests:
            await update.message.reply_text(
                f"*Request ID:* {req[0]}\n*Status:* {req[11]}",
                parse_mode="Markdown"
            )
        logger.info(f"Consultation status shown for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error retrieving consultation status for user {user_id}: {e}")
        await update.message.reply_text(get_translated_text("consultation_error", lang))

def get_consultation_handler():
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
            fallbacks=[CommandHandler("cancel", cancel_consultation)],
        ),
        CommandHandler("consult_status", consult_status),
    ]
