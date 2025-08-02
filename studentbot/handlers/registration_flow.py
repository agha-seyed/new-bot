import re
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
    CallbackQueryHandler
)
from telegram.error import TelegramError
from studentbot.utils.common import get_translated_text, sanitize_markdown  # Changed from text_formatter
from studentbot.utils.db_utils import create_user, get_user, AsyncSessionLocal, log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

logger = logging.getLogger(__name__)

FIRST_NAME, LAST_NAME, AGE, EMAIL, COUNTRY, FIELD_OF_STUDY, CONFIRM = range(7)

async def prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, prompt_text: str, next_state: int) -> int:
    """Send a prompt message and return the next state."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text(prompt_text, lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        logger.info(f"✅ Prompt {prompt_text} sent to user {user_id}")
        return next_state
    except TelegramError as e:
        logger.error(f"❌ Telegram error sending prompt {prompt_text} to user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def start_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the registration process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        async with AsyncSessionLocal() as session:
            if await get_user(session, user_id):
                await update.message.reply_text(
                    sanitize_markdown(get_translated_text("already_registered", lang)),
                    parse_mode="MarkdownV2",
                    reply_markup=ReplyKeyboardRemove()
                )
                return ConversationHandler.END
        
        context.user_data.clear()
        context.user_data["lang"] = lang
        logger.info(f"✅ User {user_id} started registration")
        await award_points_for_action(user_id, "interaction")
        await log_event(user_id, "registration_started", "Started registration process")
        return await prompt(update, context, "first_name_prompt", FIRST_NAME)
    except TelegramError as e:
        logger.error(f"❌ Telegram error starting registration for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def first_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle first name input."""
    user_id = update.effective_user.id
    context.user_data["first_name"] = update.message.text.strip()
    logger.info(f"✅ User {user_id} submitted first name: {context.user_data['first_name']}")
    return await prompt(update, context, "last_name_prompt", LAST_NAME)

async def last_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle last name input."""
    user_id = update.effective_user.id
    context.user_data["last_name"] = update.message.text.strip()
    logger.info(f"✅ User {user_id} submitted last name: {context.user_data['last_name']}")
    return await prompt(update, context, "age_prompt", AGE)

async def age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle age input with validation."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    age = update.message.text.strip()
    
    try:
        age = int(age)
        if not 0 <= age <= 120:
            raise ValueError("Age out of range")
        context.user_data["age"] = age
        logger.info(f"✅ User {user_id} submitted age: {age}")
        return await prompt(update, context, "email_prompt", EMAIL)
    except ValueError:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_age", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Invalid age input by user {user_id}: {age}")
        return AGE

async def email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle email input with validation."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    email = update.message.text.strip()
    
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_email", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Invalid email input by user {user_id}: {email}")
        return EMAIL
    
    context.user_data["email"] = email
    logger.info(f"✅ User {user_id} submitted email: {email}")
    return await prompt(update, context, "country_prompt", COUNTRY)

async def country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle country input."""
    user_id = update.effective_user.id
    context.user_data["country"] = update.message.text.strip()
    logger.info(f"✅ User {user_id} submitted country: {context.user_data['country']}")
    return await prompt(update, context, "field_of_study_prompt", FIELD_OF_STUDY)

async def field_of_study(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle field of study input and show summary."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    context.user_data["field_of_study"] = update.message.text.strip()
    
    try:
        summary = f"""
*{sanitize_markdown(get_translated_text('registration_summary', lang))}*

👤 *{sanitize_markdown(context.user_data['first_name'])}* *{sanitize_markdown(context.user_data['last_name'])}*
📆 *{context.user_data['age']}*  
📧 *{sanitize_markdown(context.user_data['email'])}*  
🌍 *{sanitize_markdown(context.user_data['country'])}*  
🎓 *{sanitize_markdown(context.user_data['field_of_study'])}*  

{sanitize_markdown(get_translated_text('confirm_registration_prompt', lang))}
        """
        keyboard = [
            [InlineKeyboardButton(get_translated_text("confirm_button", lang), callback_data="confirm_registration")],
            [InlineKeyboardButton(get_translated_text("cancel_button", lang), callback_data="cancel_registration")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            summary,
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        logger.info(f"✅ User {user_id} submitted field of study: {context.user_data['field_of_study']}")
        return CONFIRM
    except TelegramError as e:
        logger.error(f"❌ Telegram error showing summary to user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle registration confirmation."""
    query = update.callback_query
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await query.answer()
        if query.data != "confirm_registration":
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("registration_cancelled", lang)),
                parse_mode="MarkdownV2",
                reply_markup=ReplyKeyboardRemove()
            )
            await log_event(user_id, "registration_cancelled", "Cancelled registration process")
            logger.info(f"✅ User {user_id} cancelled registration")
            context.user_data.clear()
            context.user_data["lang"] = lang
            return ConversationHandler.END

        user_data = context.user_data
        async with AsyncSessionLocal() as session:
            if await get_user(session, user_id):
                await query.edit_message_text(
                    sanitize_markdown(get_translated_text("already_registered", lang)),
                    parse_mode="MarkdownV2",
                    reply_markup=ReplyKeyboardRemove()
                )
                return ConversationHandler.END

            # Save to DB
            await create_user(
                session,
                user_id,
                user_data["first_name"],
                user_data["last_name"],
                user_data["age"],
                user_data["email"],
                user_data["country"],
                user_data["field_of_study"],
            )

        # Save to Google Sheets
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        await gsheets_client.add_interaction_to_sheet(
            "users",
            [
                user_id,
                user_data["first_name"],
                user_data["last_name"] or "N/A",
                user_data["age"] or 0,
                user_data["email"] or "N/A",
                user_data["field_of_study"] or "N/A",
                user_data["country"] or "N/A",
                timestamp,
            ]
        )

        # Notify admin
        admin_chat_id = config.ADMIN_CHAT_ID
        if admin_chat_id:
            await context.bot.send_message(
                chat_id=admin_chat_id,
                text=sanitize_markdown(
                    get_translated_text("admin_new_registration", lang).format(
                        first_name=user_data["first_name"],
                        last_name=user_data["last_name"] or "N/A",
                        email=user_data["email"] or "N/A",
                        country=user_data["country"] or "N/A",
                        field=user_data["field_of_study"] or "N/A",
                        age=user_data["age"] or 0,
                        timestamp=timestamp
                    )
                ),
                parse_mode="MarkdownV2"
            )

        await query.edit_message_text(
            sanitize_markdown(get_translated_text("registration_complete", lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        await award_points_for_action(user_id, "registration")
        await log_event(user_id, "registration_completed", f"Registered user: {user_data['first_name']} {user_data['last_name']}")
        logger.info(f"✅ User {user_id} completed registration")
        context.user_data.clear()
        context.user_data["lang"] = lang
        return ConversationHandler.END
    except TelegramError as e:
        logger.error(f"❌ Telegram error confirming registration for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Unexpected error confirming registration for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle registration cancellation."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("registration_cancelled", lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        await log_event(user_id, "registration_cancelled", "Cancelled registration via command")
        logger.info(f"✅ User {user_id} cancelled registration")
        context.user_data.clear()
        context.user_data["lang"] = lang
        return ConversationHandler.END
    except TelegramError as e:
        logger.error(f"❌ Telegram error cancelling registration for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

def get_registration_handler():
    """Return the registration handler."""
    return ConversationHandler(
        entry_points=[CommandHandler("register", start_registration)],
        states={
            FIRST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, first_name)],
            LAST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, last_name)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, email)],
            COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, country)],
            FIELD_OF_STUDY: [MessageHandler(filters.TEXT & ~filters.COMMAND, field_of_study)],
            CONFIRM: [
                CallbackQueryHandler(confirm, pattern="^(confirm_registration|cancel_registration)$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, cancel)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )
