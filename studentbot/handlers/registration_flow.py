from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from studentbot.utils.text_formatter import get_translated_text
from studentbot.utils.db_utils import create_user
from studentbot.utils.gsheets import add_user_to_sheet

# States
FIRST_NAME, LAST_NAME, AGE, EMAIL, COUNTRY, FIELD_OF_STUDY = range(6)


async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the registration conversation."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("first_name_prompt", lang))
    return FIRST_NAME


async def first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the first name and asks for the last name."""
    context.user_data["first_name"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("last_name_prompt", lang))
    return LAST_NAME


async def last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the last name and asks for the age."""
    context.user_data["last_name"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("age_prompt", lang))
    return AGE


async def age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the age and asks for the email."""
    context.user_data["age"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("email_prompt", lang))
    return EMAIL


async def email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the email and asks for the country."""
    context.user_data["email"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("country_prompt", lang))
    return COUNTRY


async def country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the country and asks for the field of study."""
    context.user_data["country"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("field_of_study_prompt", lang))
    return FIELD_OF_STUDY


async def field_of_study(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the field of study and ends the conversation."""
    context.user_data["field_of_study"] = update.message.text
    lang = context.user_data.get("lang", "en")

    # Save data to database and Google Sheets
    user_data = context.user_data
    user_id = update.message.from_user.id
    create_user(
        user_id,
        user_data["first_name"],
        user_data["last_name"],
        user_data["age"],
        user_data["email"],
        user_data["country"],
        user_data["field_of_study"],
    )
    add_user_to_sheet(
        "users",
        [
            user_id,
            user_data["first_name"],
            user_data["last_name"],
            user_data["age"],
            user_data["email"],
            user_data["country"],
            user_data["field_of_study"],
        ],
    )

    await update.message.reply_text(get_translated_text("registration_complete", lang))
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("registration_cancelled", lang))
    return ConversationHandler.END


def get_registration_handler():
    """Returns the registration conversation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler("register", start_registration)],
        states={
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_name)],
            LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, last_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, email)],
            COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, country)],
            FIELD_OF_STUDY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, field_of_study)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
