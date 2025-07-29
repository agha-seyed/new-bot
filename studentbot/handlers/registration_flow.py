import re
import os
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from ..utils.text_formatter import get_translated_text, sanitize_markdown
from ..utils.db_utils import create_user, add_points, get_user, log_event
from ..utils.gsheets import add_user_to_sheet

# Set up logging
logger = logging.getLogger(__name__)

# States
FIRST_NAME, LAST_NAME, AGE, EMAIL, COUNTRY, FIELD_OF_STUDY, CONFIRM = range(7)


async def prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt_text, next_state) -> int:
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text(prompt_text, lang))
    return next_state


async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    logger.info(f"User {update.message.from_user.id} started registration.")
    return await prompt(update, context, "first_name_prompt", FIRST_NAME)


async def first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["first_name"] = update.message.text
    return await prompt(update, context, "last_name_prompt", LAST_NAME)


async def last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["last_name"] = update.message.text
    return await prompt(update, context, "age_prompt", AGE)


async def age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    age = update.message.text
    if not age.isdigit():
        await update.message.reply_text(get_translated_text("invalid_age", lang))
        return AGE
    context.user_data["age"] = int(age)
    return await prompt(update, context, "email_prompt", EMAIL)


async def email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    email = update.message.text
    if not re.match(r"[^@]+@[^@]+\\.[^@]+", email):
        await update.message.reply_text(get_translated_text("invalid_email", lang))
        return EMAIL
    context.user_data["email"] = email
    return await prompt(update, context, "country_prompt", COUNTRY)


async def country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["country"] = update.message.text
    return await prompt(update, context, "field_of_study_prompt", FIELD_OF_STUDY)


async def field_of_study(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["field_of_study"] = update.message.text
    lang = context.user_data.get("lang", "en")

    summary = f"""
{get_translated_text('registration_summary', lang)}

👤 *{sanitize_markdown(context.user_data['first_name'])}* {sanitize_markdown(context.user_data['last_name'])}
📆 *{context.user_data['age']}*  
📧 *{sanitize_markdown(context.user_data['email'])}*  
🌍 *{sanitize_markdown(context.user_data['country'])}*  
🎓 *{sanitize_markdown(context.user_data['field_of_study'])}*  

{get_translated_text('confirm_registration_prompt', lang)}
    """
    keyboard = [[get_translated_text("yes", lang), get_translated_text("no", lang)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(summary, parse_mode="MarkdownV2", reply_markup=reply_markup)
    return CONFIRM


async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    if update.message.text != get_translated_text("yes", lang):
        await update.message.reply_text(get_translated_text("registration_cancelled", lang))
        return ConversationHandler.END

    user_data = context.user_data
    user_id = update.message.from_user.id
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # Check for duplicate
    if get_user(user_id):
        await update.message.reply_text(get_translated_text("already_registered", lang))
        return ConversationHandler.END

    # Save to DB and Sheets
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
            timestamp,
        ],
    )
    add_points(user_id, 10)
    log_event(user_id, "registration")

    # Notify admin
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")
    if admin_chat_id:
        await context.bot.send_message(
            chat_id=admin_chat_id,
            text=f"New registration:\n\nName: {user_data['first_name']} {user_data['last_name']}\nEmail: {user_data['email']}\nCountry: {user_data['country']}\nField: {user_data['field_of_study']}\nAge: {user_data['age']}\nTime: {timestamp}"
        )

    await update.message.reply_text(get_translated_text("registration_complete", lang))
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("registration_cancelled", lang))
    return ConversationHandler.END


def get_registration_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("register", start_registration)],
        states={
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_name)],
            LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, last_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, email)],
            COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, country)],
            FIELD_OF_STUDY: [MessageHandler(filters.TEXT & ~filters.COMMAND, field_of_study)],
            CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
