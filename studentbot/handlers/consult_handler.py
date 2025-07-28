import os
import os
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

import os
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from utils.text_formatter import get_translated_text
from utils.db_utils import create_consultation_request, get_consultation_requests
from utils.gdrive import upload_file

# States
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


async def start_consultation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the consultation conversation."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("consultation_name_prompt", lang))
    return NAME


async def name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the name and asks for the field of study."""
    context.user_data["consultation_name"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(
        get_translated_text("consultation_field_of_study_prompt", lang)
    )
    return FIELD_OF_STUDY


async def field_of_study(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the field of study and asks for the level."""
    context.user_data["consultation_field_of_study"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("consultation_level_prompt", lang))
    return LEVEL


async def level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the level and asks for the GPA."""
    context.user_data["consultation_level"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("consultation_gpa_prompt", lang))
    return GPA


async def gpa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the GPA and asks for the destination country."""
    context.user_data["consultation_gpa"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(
        get_translated_text("consultation_destination_country_prompt", lang)
    )
    return DESTINATION_COUNTRY


async def destination_country(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Stores the destination country and asks for the language level."""
    context.user_data["consultation_destination_country"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(
        get_translated_text("consultation_language_level_prompt", lang)
    )
    return LANGUAGE_LEVEL


async def language_level(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the language level and asks for the budget."""
    context.user_data["consultation_language_level"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("consultation_budget_prompt", lang))
    return BUDGET


async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the budget and asks for the work experience."""
    context.user_data["consultation_budget"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(
        get_translated_text("consultation_work_experience_prompt", lang)
    )
    return WORK_EXPERIENCE


async def work_experience(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the work experience and asks for any special needs."""
    context.user_data["consultation_work_experience"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(
        get_translated_text("consultation_special_needs_prompt", lang)
    )
    return SPECIAL_NEEDS


async def special_needs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores any special needs and asks for the user to upload their resume."""
    context.user_data["consultation_special_needs"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(
        get_translated_text("consultation_upload_resume_prompt", lang)
    )
    return UPLOAD_RESUME


async def upload_resume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the resume and ends the conversation."""
    lang = context.user_data.get("lang", "en")
    document = update.message.document
    file = await context.bot.get_file(document.file_id)
    file_path = f"{document.file_name}"
    await file.download_to_drive(file_path)
    user_id = update.message.from_user.id
    upload_file(file_path, user_id, document.file_name)
    os.remove(file_path)

    # Save data to database
    user_data = context.user_data
    create_consultation_request(
        user_id,
        user_data["consultation_name"],
        user_data["consultation_field_of_study"],
        user_data["consultation_level"],
        user_data["consultation_gpa"],
        user_data["consultation_destination_country"],
        user_data["consultation_language_level"],
        user_data["consultation_budget"],
        user_data["consultation_work_experience"],
        user_data["consultation_special_needs"],
    )

    # Notify admin
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")
    if admin_chat_id:
        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=f"New consultation request from {user_data['consultation_name']}",
        )

    await update.message.reply_text(
        get_translated_text("consultation_complete", lang)
    )
    return ConversationHandler.END


async def cancel_consultation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancels and ends the conversation."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(
        get_translated_text("consultation_cancelled", lang)
    )
    return ConversationHandler.END


async def consult_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the status of the user's consultation requests."""
    lang = context.user_data.get("lang", "en")
    user_id = update.message.from_user.id
    requests = get_consultation_requests(user_id)
    if not requests:
        await update.message.reply_text(get_translated_text("no_consultation_requests", lang))
        return

    for req in requests:
        status_text = f"""
*Request ID:* {req[0]}
*Status:* {req[11]}
        """
        await update.message.reply_text(status_text, parse_mode="Markdown")

def get_consultation_handler():
    """Returns the consultation conversation handler."""
    return [
        ConversationHandler(
            entry_points=[CommandHandler("consult", start_consultation)],
            states={
                NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, name)],
                FIELD_OF_STUDY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, field_of_study)
                ],
                LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, level)],
                GPA: [MessageHandler(filters.TEXT & ~filters.COMMAND, gpa)],
                DESTINATION_COUNTRY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, destination_country)
                ],
                LANGUAGE_LEVEL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, language_level)
                ],
                BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, budget)],
                WORK_EXPERIENCE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, work_experience)
                ],
                SPECIAL_NEEDS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, special_needs)
                ],
                UPLOAD_RESUME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, upload_resume)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel_consultation)],
        ),
        CommandHandler("consult_status", consult_status),
    ]
