import logging
import re
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import get_user, update_user
from studentbot.utils.gsheets import update_user_in_sheet
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# States
(
    EDIT_FIRST_NAME,
    EDIT_LAST_NAME,
    EDIT_AGE,
    EDIT_EMAIL,
    EDIT_COUNTRY,
    EDIT_FIELD_OF_STUDY,
    CONFIRM_EDIT,
) = range(7)

CANCEL_BUTTON = "❌ Cancel / لغو"
CONFIRM_BUTTON = "✅ Confirm / تایید"


async def start_edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    user_id = update.message.from_user.id
    user = get_user(user_id)
    context.user_data["user"] = user
    reply_markup = ReplyKeyboardMarkup([[CANCEL_BUTTON]], one_time_keyboard=True, resize_keyboard=True)
    logger.info(f"User {user_id} started editing profile.")
    await update.message.reply_text(
        f"👤 " + get_translated_text("edit_first_name_prompt", lang).format(first_name=sanitize_markdown(user[1])),
        reply_markup=reply_markup
    )
    return EDIT_FIRST_NAME


async def edit_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == CANCEL_BUTTON:
        return await cancel_edit(update, context)
    context.user_data["new_first_name"] = sanitize_markdown(update.message.text)
    lang = context.user_data.get("lang", "en")
    user = context.user_data["user"]
    await update.message.reply_text(
        f"👥 " + get_translated_text("edit_last_name_prompt", lang).format(last_name=sanitize_markdown(user[2]))
    )
    return EDIT_LAST_NAME


async def edit_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == CANCEL_BUTTON:
        return await cancel_edit(update, context)
    context.user_data["new_last_name"] = sanitize_markdown(update.message.text)
    lang = context.user_data.get("lang", "en")
    user = context.user_data["user"]
    await update.message.reply_text(
        f"🎂 " + get_translated_text("edit_age_prompt", lang).format(age=user[3])
    )
    return EDIT_AGE


async def edit_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == CANCEL_BUTTON:
        return await cancel_edit(update, context)
    try:
        age = int(update.message.text)
        context.user_data["new_age"] = age
    except ValueError:
        lang = context.user_data.get("lang", "en")
        await update.message.reply_text(get_translated_text("invalid_age", lang))
        return EDIT_AGE
    lang = context.user_data.get("lang", "en")
    user = context.user_data["user"]
    await update.message.reply_text(
        f"📧 " + get_translated_text("edit_email_prompt", lang).format(email=sanitize_markdown(user[4]))
    )
    return EDIT_EMAIL


async def edit_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == CANCEL_BUTTON:
        return await cancel_edit(update, context)
    email = update.message.text
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        lang = context.user_data.get("lang", "en")
        await update.message.reply_text(get_translated_text("invalid_email", lang))
        return EDIT_EMAIL
    context.user_data["new_email"] = sanitize_markdown(email)
    lang = context.user_data.get("lang", "en")
    user = context.user_data["user"]
    await update.message.reply_text(
        f"🌍 " + get_translated_text("edit_country_prompt", lang).format(country=sanitize_markdown(user[5]))
    )
    return EDIT_COUNTRY


async def edit_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == CANCEL_BUTTON:
        return await cancel_edit(update, context)
    context.user_data["new_country"] = sanitize_markdown(update.message.text)
    lang = context.user_data.get("lang", "en")
    user = context.user_data["user"]
    await update.message.reply_text(
        f"📚 " + get_translated_text("edit_field_of_study_prompt", lang).format(field_of_study=sanitize_markdown(user[6]))
    )
    return EDIT_FIELD_OF_STUDY


async def edit_field_of_study(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == CANCEL_BUTTON:
        return await cancel_edit(update, context)
    context.user_data["new_field_of_study"] = sanitize_markdown(update.message.text)
    lang = context.user_data.get("lang", "en")
    user_data = context.user_data

    preview = f"""
👤 *{get_translated_text("first_name", lang)}:* {user_data["new_first_name"]}
👥 *{get_translated_text("last_name", lang)}:* {user_data["new_last_name"]}
🎂 *{get_translated_text("age", lang)}:* {user_data["new_age"]}
📧 *{get_translated_text("email", lang)}:* {user_data["new_email"]}
🌍 *{get_translated_text("country", lang)}:* {user_data["new_country"]}
📚 *{get_translated_text("field_of_study", lang)}:* {user_data["new_field_of_study"]}
    """
    keyboard = ReplyKeyboardMarkup(
        [[CONFIRM_BUTTON], [CANCEL_BUTTON]], resize_keyboard=True, one_time_keyboard=True
    )
    await update.message.reply_text(
        get_translated_text("preview_updated_info", lang) + "\n" + preview.strip(),
        parse_mode="MarkdownV2",
        reply_markup=keyboard,
    )
    return CONFIRM_EDIT


async def confirm_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == CANCEL_BUTTON:
        return await cancel_edit(update, context)

    lang = context.user_data.get("lang", "en")
    user_data = context.user_data
    user_id = update.message.from_user.id

    try:
        update_user(
            user_id,
            user_data["new_first_name"],
            user_data["new_last_name"],
            user_data["new_age"],
            user_data["new_email"],
            user_data["new_country"],
            user_data["new_field_of_study"],
        )
        update_user_in_sheet(
            "users",
            user_id,
            [
                user_id,
                user_data["new_first_name"],
                user_data["new_last_name"],
                user_data["new_age"],
                user_data["new_email"],
                user_data["new_country"],
                user_data["new_field_of_study"],
                datetime.now().strftime("%Y-%m-%d %H:%M"),
            ],
        )
        logger.info(f"User {user_id} updated profile.")

        # Notify admin
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if admin_chat_id:
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=f"🔔 User {user_data['new_first_name']} {user_data['new_last_name']} updated their profile."
            )

    except Exception as e:
        logger.error(f"Error updating user profile: {e}")
        await update.message.reply_text(get_translated_text("edit_failed", lang))
        return ConversationHandler.END

    await update.message.reply_text(get_translated_text("profile_updated", lang))
    return ConversationHandler.END


async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("edit_cancelled", lang))
    logger.info(f"User {update.message.from_user.id} cancelled editing.")
    return ConversationHandler.END


def get_edit_profile_handler():
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^✏️"), start_edit_profile)
        ],
        states={
            EDIT_FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_first_name)],
            EDIT_LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_last_name)],
            EDIT_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_age)],
            EDIT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_email)],
            EDIT_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_country)],
            EDIT_FIELD_OF_STUDY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field_of_study)],
            CONFIRM_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_edit)],
        },
        fallbacks=[CommandHandler("cancel", cancel_edit)],
    )
