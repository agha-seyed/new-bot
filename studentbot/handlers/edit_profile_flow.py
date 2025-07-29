from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from ..utils.text_formatter import get_translated_text
from ..utils.db_utils import get_user, update_user
from ..utils.gsheets import update_user_in_sheet

# States
(
    EDIT_FIRST_NAME,
    EDIT_LAST_NAME,
    EDIT_AGE,
    EDIT_EMAIL,
    EDIT_COUNTRY,
    EDIT_FIELD_OF_STUDY,
) = range(6)


async def start_edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the edit profile conversation."""
    lang = context.user_data.get("lang", "en")
    user_id = update.message.from_user.id
    user = get_user(user_id)
    context.user_data["user"] = user
    await update.message.reply_text(
        get_translated_text("edit_first_name_prompt", lang).format(first_name=user[1])
    )
    return EDIT_FIRST_NAME


async def edit_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the new first name and asks for the new last name."""
    context.user_data["new_first_name"] = update.message.text
    lang = context.user_data.get("lang", "en")
    user = context.user_data["user"]
    await update.message.reply_text(
        get_translated_text("edit_last_name_prompt", lang).format(last_name=user[2])
    )
    return EDIT_LAST_NAME


async def edit_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the new last name and asks for the new age."""
    context.user_data["new_last_name"] = update.message.text
    lang = context.user_data.get("lang", "en")
    user = context.user_data["user"]
    await update.message.reply_text(
        get_translated_text("edit_age_prompt", lang).format(age=user[3])
    )
    return EDIT_AGE


async def edit_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the new age and asks for the new email."""
    context.user_data["new_age"] = update.message.text
    lang = context.user_data.get("lang", "en")
    user = context.user_data["user"]
    await update.message.reply_text(
        get_translated_text("edit_email_prompt", lang).format(email=user[4])
    )
    return EDIT_EMAIL


async def edit_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the new email and asks for the new country."""
    context.user_data["new_email"] = update.message.text
    lang = context.user_data.get("lang", "en")
    user = context.user_data["user"]
    await update.message.reply_text(
        get_translated_text("edit_country_prompt", lang).format(country=user[5])
    )
    return EDIT_COUNTRY


async def edit_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the new country and asks for the new field of study."""
    context.user_data["new_country"] = update.message.text
    lang = context.user_data.get("lang", "en")
    user = context.user_data["user"]
    await update.message.reply_text(
        get_translated_text("edit_field_of_study_prompt", lang).format(
            field_of_study=user[6]
        )
    )
    return EDIT_FIELD_OF_STUDY


async def edit_field_of_study(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Stores the new field of study and ends the conversation."""
    context.user_data["new_field_of_study"] = update.message.text
    lang = context.user_data.get("lang", "en")

    # Save data to database and Google Sheets
    user_data = context.user_data
    user_id = update.message.from_user.id
    update_user(
        user_id,
        user_data.get("new_first_name", user_data["user"][1]),
        user_data.get("new_last_name", user_data["user"][2]),
        user_data.get("new_age", user_data["user"][3]),
        user_data.get("new_email", user_data["user"][4]),
        user_data.get("new_country", user_data["user"][5]),
        user_data.get("new_field_of_study", user_data["user"][6]),
    )
    update_user_in_sheet(
        "users",
        user_id,
        [
            user_id,
            user_data.get("new_first_name", user_data["user"][1]),
            user_data.get("new_last_name", user_data["user"][2]),
            user_data.get("new_age", user_data["user"][3]),
            user_data.get("new_email", user_data["user"][4]),
            user_data.get("new_country", user_data["user"][5]),
            user_data.get("new_field_of_study", user_data["user"][6]),
        ],
    )

    await update.message.reply_text(get_translated_text("profile_updated", lang))
    return ConversationHandler.END


async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("edit_cancelled", lang))
    return ConversationHandler.END


def get_edit_profile_handler():
    """Returns the edit profile conversation handler."""
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^✏️"), start_edit_profile)
        ],
        states={
            EDIT_FIRST_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_first_name)
            ],
            EDIT_LAST_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_last_name)
            ],
            EDIT_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_age)],
            EDIT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_email)],
            EDIT_COUNTRY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_country)
            ],
            EDIT_FIELD_OF_STUDY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field_of_study)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_edit)],
    )
