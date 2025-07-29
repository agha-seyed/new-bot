import logging
import re
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import get_user, update_user, AsyncSessionLocal
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

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


async def start_edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the profile editing process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        async with AsyncSessionLocal() as session:
            user = await get_user(user_id, session)
        if not user:
            await update.message.reply_text(
                sanitize_markdown(get_translated_text("not_registered", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ User {user_id} not registered")
            return ConversationHandler.END
        
        context.user_data["user"] = user
        reply_markup = ReplyKeyboardMarkup(
            [[get_translated_text("cancel_button", lang)]],
            one_time_keyboard=True,
            resize_keyboard=True
        )
        await update.message.reply_text(
            f"👤 {sanitize_markdown(get_translated_text('edit_first_name_prompt', lang).format(first_name=sanitize_markdown(user[1])))}",
            reply_markup=reply_markup,
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ User {user_id} started editing profile")
        await award_points_for_action(user_id, "interaction")
        return EDIT_FIRST_NAME
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Unexpected error for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
        return ConversationHandler.END


async def edit_first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle first name edit."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    if update.message.text == get_translated_text("cancel_button", lang):
        return await cancel_edit(update, context)
    
    context.user_data["new_first_name"] = sanitize_markdown(update.message.text)
    user = context.user_data["user"]
    await update.message.reply_text(
        f"👥 {sanitize_markdown(get_translated_text('edit_last_name_prompt', lang).format(last_name=sanitize_markdown(user[2])))}",
        parse_mode="MarkdownV2"
    )
    logger.info(f"✅ User {user_id} entered new first name: {context.user_data['new_first_name']}")
    return EDIT_LAST_NAME


async def edit_last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle last name edit."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    if update.message.text == get_translated_text("cancel_button", lang):
        return await cancel_edit(update, context)
    
    context.user_data["new_last_name"] = sanitize_markdown(update.message.text)
    user = context.user_data["user"]
    await update.message.reply_text(
        f"🎂 {sanitize_markdown(get_translated_text('edit_age_prompt', lang).format(age=user[3]))}",
        parse_mode="MarkdownV2"
    )
    logger.info(f"✅ User {user_id} entered new last name: {context.user_data['new_last_name']}")
    return EDIT_AGE


async def edit_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle age edit."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    if update.message.text == get_translated_text("cancel_button", lang):
        return await cancel_edit(update, context)
    
    try:
        age = int(update.message.text)
        if age < 0 or age > 120:
            raise ValueError("Invalid age range")
        context.user_data["new_age"] = age
        user = context.user_data["user"]
        await update.message.reply_text(
            f"📧 {sanitize_markdown(get_translated_text('edit_email_prompt', lang).format(email=sanitize_markdown(user[4])))}",
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ User {user_id} entered new age: {age}")
        return EDIT_EMAIL
    except ValueError:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_age", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Invalid age input by user {user_id}: {update.message.text}")
        return EDIT_AGE


async def edit_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle email edit."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    if update.message.text == get_translated_text("cancel_button", lang):
        return await cancel_edit(update, context)
    
    email = update.message.text
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_email", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Invalid email input by user {user_id}: {email}")
        return EDIT_EMAIL
    
    context.user_data["new_email"] = sanitize_markdown(email)
    user = context.user_data["user"]
    await update.message.reply_text(
        f"🌍 {sanitize_markdown(get_translated_text('edit_country_prompt', lang).format(country=sanitize_markdown(user[5])))}",
        parse_mode="MarkdownV2"
    )
    logger.info(f"✅ User {user_id} entered new email: {email}")
    return EDIT_COUNTRY


async def edit_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle country edit."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    if update.message.text == get_translated_text("cancel_button", lang):
        return await cancel_edit(update, context)
    
    context.user_data["new_country"] = sanitize_markdown(update.message.text)
    user = context.user_data["user"]
    await update.message.reply_text(
        f"📚 {sanitize_markdown(get_translated_text('edit_field_of_study_prompt', lang).format(field_of_study=sanitize_markdown(user[6])))}",
        parse_mode="MarkdownV2"
    )
    logger.info(f"✅ User {user_id} entered new country: {context.user_data['new_country']}")
    return EDIT_FIELD_OF_STUDY


async def edit_field_of_study(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle field of study edit."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    if update.message.text == get_translated_text("cancel_button", lang):
        return await cancel_edit(update, context)
    
    context.user_data["new_field_of_study"] = sanitize_markdown(update.message.text)
    user_data = context.user_data

    preview = f"""
🌟 *{sanitize_markdown(get_translated_text("profile_preview", lang))}*
👤 *{sanitize_markdown(get_translated_text("first_name", lang))}*: {sanitize_markdown(user_data["new_first_name"])}
👥 *{sanitize_markdown(get_translated_text("last_name", lang))}*: {sanitize_markdown(user_data["new_last_name"])}
🎂 *{sanitize_markdown(get_translated_text("age", lang))}*: {user_data["new_age"]}
📧 *{sanitize_markdown(get_translated_text("email", lang))}*: {sanitize_markdown(user_data["new_email"])}
🌍 *{sanitize_markdown(get_translated_text("country", lang))}*: {sanitize_markdown(user_data["new_country"])}
📚 *{sanitize_markdown(get_translated_text("field_of_study", lang))}*: {sanitize_markdown(user_data["new_field_of_study"])}
    """
    keyboard = ReplyKeyboardMarkup(
        [[get_translated_text("confirm_button", lang), get_translated_text("cancel_button", lang)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text(
        sanitize_markdown(get_translated_text("preview_updated_info", lang)) + "\n" + preview,
        parse_mode="MarkdownV2",
        reply_markup=keyboard
    )
    logger.info(f"✅ User {user_id} previewed profile changes")
    return CONFIRM_EDIT


async def confirm_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Confirm and save profile changes."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    if update.message.text == get_translated_text("cancel_button", lang):
        return await cancel_edit(update, context)
    
    if update.message.text != get_translated_text("confirm_button", lang):
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_confirmation", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Invalid confirmation input by user {user_id}: {update.message.text}")
        return CONFIRM_EDIT

    user_data = context.user_data
    
    try:
        async with AsyncSessionLocal() as session:
            await update_user(
                session,
                user_id,
                user_data["new_first_name"],
                user_data["new_last_name"],
                user_data["new_age"],
                user_data["new_email"],
                user_data["new_country"],
                user_data["new_field_of_study"]
            )
        
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id,
                user_data["new_first_name"],
                user_data["new_last_name"],
                user_data["new_age"],
                user_data["new_email"],
                user_data["new_country"],
                user_data["new_field_of_study"],
                "Profile Update",
                "Updated profile details",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
        
        # Notify admin
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if admin_chat_id:
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=sanitize_markdown(
                    get_translated_text("admin_profile_updated", lang).format(
                        first_name=user_data["new_first_name"],
                        last_name=user_data["new_last_name"]
                    )
                ),
                parse_mode="MarkdownV2"
            )
        
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("profile_updated", lang)),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ User {user_id} updated profile")
        await award_points_for_action(user_id, "registration")
        return ConversationHandler.END
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Error updating profile for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("edit_failed", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END


async def cancel_edit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the profile editing process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("edit_cancelled", lang)),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ User {user_id} cancelled profile editing")
        return ConversationHandler.END
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
        return ConversationHandler.END


def get_edit_profile_handler():
    """Return the edit profile conversation handler."""
    return ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^✏️"), start_edit_profile),
            CommandHandler("edit_profile", start_edit_profile)
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