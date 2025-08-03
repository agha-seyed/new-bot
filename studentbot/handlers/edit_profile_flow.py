import logging
from typing import Optional
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from telegram.error import TelegramError
from sqlalchemy import update
from studentbot.utils.common import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import AsyncSessionLocal, get_user, log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.utils.models_db import User
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

logger = logging.getLogger(__name__)

# States
SELECT_FIELD, EDIT_NAME, EDIT_AGE, EDIT_EMAIL, EDIT_FIELD_OF_STUDY, EDIT_COUNTRY = range(6)  # Changed from range(5) to range(6)

async def validate_age(age_text: str) -> Optional[int]:
    """Validate age input."""
    try:
        age = int(age_text)
        if not 15 <= age <= 100:
            raise ValueError("Age must be between 15 and 100.")
        return age
    except ValueError:
        return None

async def validate_email(email: str) -> bool:
    """Validate email format."""
    import re
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return bool(re.match(pattern, email))

async def start_edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the profile editing process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        user = await get_user(user_id)
        if not user:
            await update.message.reply_text(
                sanitize_markdown(get_translated_text("not_registered", lang)),
                parse_mode="MarkdownV2"
            )
            return ConversationHandler.END
        profile_summary = (
            f"👤 *{sanitize_markdown(get_translated_text('profile_summary', lang))}*\n\n"
            f"📛 *{sanitize_markdown(get_translated_text('name', lang))}*: {sanitize_markdown(user.first_name)} {sanitize_markdown(user.last_name or 'N/A')}\n"
            f"🎂 *{sanitize_markdown(get_translated_text('age', lang))}*: {user.age or 'N/A'}\n"
            f"📧 *{sanitize_markdown(get_translated_text('email', lang))}*: {sanitize_markdown(user.email or 'N/A')}\n"
            f"🎓 *{sanitize_markdown(get_translated_text('field_of_study', lang))}*: {sanitize_markdown(user.field_of_study or 'N/A')}\n"
            f"🌍 *{sanitize_markdown(get_translated_text('country', lang))}*: {sanitize_markdown(user.country or 'N/A')}"
        )
        keyboard = [
            [InlineKeyboardButton(get_translated_text("edit_name", lang), callback_data="edit_name")],
            [InlineKeyboardButton(get_translated_text("edit_age", lang), callback_data="edit_age")],
            [InlineKeyboardButton(get_translated_text("edit_email", lang), callback_data="edit_email")],
            [InlineKeyboardButton(get_translated_text("edit_field_of_study", lang), callback_data="edit_field_of_study")],
            [InlineKeyboardButton(get_translated_text("edit_country", lang), callback_data="edit_country")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            profile_summary,
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        logger.info(f"👤 User {user_id} started profile editing")
        await award_points_for_action(user_id, "interaction")
        return SELECT_FIELD
    except TelegramError as e:
        logger.error(f"❌ Telegram error starting profile edit for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def select_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle field selection for editing."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    field = query.data
    
    try:
        prompts = {
            "edit_name": ("name_prompt", EDIT_NAME),
            "edit_age": ("age_prompt", EDIT_AGE),
            "edit_email": ("email_prompt", EDIT_EMAIL),
            "edit_field_of_study": ("field_of_study_prompt", EDIT_FIELD_OF_STUDY),
            "edit_country": ("country_prompt", EDIT_COUNTRY)
        }
        if field not in prompts:
            await query.message.reply_text(
                sanitize_markdown(get_translated_text("invalid_selection", lang)),
                parse_mode="MarkdownV2"
            )
            return SELECT_FIELD
        
        prompt_key, next_state = prompts[field]
        context.user_data["edit_field"] = field
        await query.message.reply_text(
            sanitize_markdown(get_translated_text(prompt_key, lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        logger.info(f"✅ User {user_id} selected field to edit: {field}")
        return next_state
    except TelegramError as e:
        logger.error(f"❌ Telegram error selecting field for user {user_id}: {str(e)}")
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def edit_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle name editing."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    name = update.message.text.strip()
    
    if not name or len(name) < 2:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_name", lang)),
            parse_mode="MarkdownV2"
        )
        return EDIT_NAME
    
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                parts = name.split(maxsplit=1)
                first_name = parts[0]
                last_name = parts[1] if len(parts) > 1 else None
                await session.execute(
                    update(User).where(User.id == user_id).values(
                        first_name=first_name, last_name=last_name
                    )
                )
                await session.commit()
        
        user = await get_user(user_id)
        interaction_data = [
            user_id,
            user.first_name,
            user.last_name or "N/A",
            user.age or 0,
            user.email or "N/A",
            user.field_of_study or "N/A",
            user.country or "N/A",
            "Profile Edit",
            f"Updated name to {name}",
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        ]
        await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("profile_updated", lang)),
            parse_mode="MarkdownV2"
        )
        await award_points_for_action(user_id, "profile_edit")
        await log_event(user_id, "profile_updated", f"Name updated to {name}")
        logger.info(f"✅ User {user_id} updated name: {name}")
        return await start_edit_profile(update, context)  # Return to field selection
    except TelegramError as e:
        logger.error(f"❌ Telegram error updating name for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Error updating name for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def edit_age(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle age editing."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    age_text = update.message.text.strip()
    
    age = await validate_age(age_text)
    if age is None:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_age", lang)),
            parse_mode="MarkdownV2"
        )
        return EDIT_AGE
    
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    update(User).where(User.id == user_id).values(age=age)
                )
                await session.commit()
        
        user = await get_user(user_id)
        interaction_data = [
            user_id,
            user.first_name,
            user.last_name or "N/A",
            user.age or 0,
            user.email or "N/A",
            user.field_of_study or "N/A",
            user.country or "N/A",
            "Profile Edit",
            f"Updated age to {age}",
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        ]
        await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("profile_updated", lang)),
            parse_mode="MarkdownV2"
        )
        await award_points_for_action(user_id, "profile_edit")
        await log_event(user_id, "profile_updated", f"Age updated to {age}")
        logger.info(f"✅ User {user_id} updated age: {age}")
        return await start_edit_profile(update, context)
    except TelegramError as e:
        logger.error(f"❌ Telegram error updating age for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Error updating age for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def edit_email(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle email editing."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    email = update.message.text.strip()
    
    if not await validate_email(email):
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_email", lang)),
            parse_mode="MarkdownV2"
        )
        return EDIT_EMAIL
    
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    update(User).where(User.id == user_id).values(email=email)
                )
                await session.commit()
        
        user = await get_user(user_id)
        interaction_data = [
            user_id,
            user.first_name,
            user.last_name or "N/A",
            user.age or 0,
            user.email or "N/A",
            user.field_of_study or "N/A",
            user.country or "N/A",
            "Profile Edit",
            f"Updated email to {email}",
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        ]
        await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("profile_updated", lang)),
            parse_mode="MarkdownV2"
        )
        await award_points_for_action(user_id, "profile_edit")
        await log_event(user_id, "profile_updated", f"Email updated to {email}")
        logger.info(f"✅ User {user_id} updated email: {email}")
        return await start_edit_profile(update, context)
    except TelegramError as e:
        logger.error(f"❌ Telegram error updating email for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Error updating email for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def edit_field_of_study(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle field of study editing."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    field = update.message.text.strip()
    
    if not field or len(field) < 3:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_field_of_study", lang)),
            parse_mode="MarkdownV2"
        )
        return EDIT_FIELD_OF_STUDY
    
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    update(User).where(User.id == user_id).values(field_of_study=field)
                )
                await session.commit()
        
        user = await get_user(user_id)
        interaction_data = [
            user_id,
            user.first_name,
            user.last_name or "N/A",
            user.age or 0,
            user.email or "N/A",
            user.field_of_study or "N/A",
            user.country or "N/A",
            "Profile Edit",
            f"Updated field of study to {field}",
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        ]
        await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("profile_updated", lang)),
            parse_mode="MarkdownV2"
        )
        await award_points_for_action(user_id, "profile_edit")
        await log_event(user_id, "profile_updated", f"Field of study updated to {field}")
        logger.info(f"✅ User {user_id} updated field of study: {field}")
        return await start_edit_profile(update, context)
    except TelegramError as e:
        logger.error(f"❌ Telegram error updating field of study for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Error updating field of study for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def edit_country(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle country editing."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    country = update.message.text.strip()
    
    if not country or len(country) < 2:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_country", lang)),
            parse_mode="MarkdownV2"
        )
        return EDIT_COUNTRY
    
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                await session.execute(
                    update(User).where(User.id == user_id).values(country=country)
                )
                await session.commit()
        
        user = await get_user(user_id)
        interaction_data = [
            user_id,
            user.first_name,
            user.last_name or "N/A",
            user.age or 0,
            user.email or "N/A",
            user.field_of_study or "N/A",
            user.country or "N/A",
            "Profile Edit",
            f"Updated country to {country}",
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        ]
        await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("profile_updated", lang)),
            parse_mode="MarkdownV2"
        )
        await award_points_for_action(user_id, "profile_edit")
        await log_event(user_id, "profile_updated", f"Country updated to {country}")
        logger.info(f"✅ User {user_id} updated country: {country}")
        return await start_edit_profile(update, context)
    except TelegramError as e:
        logger.error(f"❌ Telegram error updating country for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Error updating country for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def cancel_edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the profile editing process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("profile_edit_cancelled", lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        context.user_data["lang"] = lang
        logger.info(f"✅ User {user_id} cancelled profile editing")
        return ConversationHandler.END
    except TelegramError as e:
        logger.error(f"❌ Telegram error cancelling profile edit for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

def get_edit_profile_handler():
    """Return the edit profile handler."""
    return [
        ConversationHandler(
            entry_points=[CommandHandler("edit_profile", start_edit_profile)],
            states={
                SELECT_FIELD: [CallbackQueryHandler(select_field, pattern="^edit_")],
                EDIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_name)],
                EDIT_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_age)],
                EDIT_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_email)],
                EDIT_FIELD_OF_STUDY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field_of_study)],
                EDIT_COUNTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_country)],
            },
            fallbacks=[CommandHandler("cancel", cancel_edit_profile)]
        )
    ]
