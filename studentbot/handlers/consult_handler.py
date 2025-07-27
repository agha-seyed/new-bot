from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from studentbot.utils.text_formatter import get_translated_text
from studentbot.utils.db_utils import create_consultation_request

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
    # TODO: Handle file upload
    lang = context.user_data.get("lang", "en")
    # Save data to database
    user_id = update.message.from_user.id
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


def get_consultation_handler():
    """Returns the consultation conversation handler."""
    return ConversationHandler(
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
    )
