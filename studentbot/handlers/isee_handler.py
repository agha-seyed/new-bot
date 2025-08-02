import logging
from typing import Optional
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
from sqlalchemy import select
from datetime import datetime
from studentbot import config
from studentbot.utils.common import get_translated_text, sanitize_markdown  # Changed from text_formatter
from studentbot.utils.db_utils import AsyncSessionLocal, get_user, log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot.utils.models_db import ISEEResult

logger = logging.getLogger(__name__)

# States
FAMILY_MEMBERS, ANNUAL_INCOME, IS_OWNER, PROPERTY_AREA = range(4)

# ISEE calculation constants (should be added to config.py)
ISEE_COEFFICIENTS = {1: 1, 2: 1.57, 3: 2.04, 4: 2.46, 5: 2.85, 6: 3.20, 7: 3.50, 8: 3.80}
PROPERTY_VALUE_FACTOR = 500
PROPERTY_VALUE_MULTIPLIER = 0.2
SCHOLARSHIP_THRESHOLDS = {
    "full": 12650,
    "medium": 16445,
    "partial": 23000,
}

async def store_isee_result(
    user_id: int, family_members: int, annual_income: float, 
    property_value: float, isee: float, status: str
) -> None:
    """Store ISEE calculation result in the database using ORM."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                isee_result = ISEEResult(
                    user_id=user_id,
                    family_members=family_members,
                    annual_income=annual_income,
                    property_value=property_value,
                    isee=isee,
                    status=status
                )
                session.add(isee_result)
                await session.commit()
                logger.info(f"✅ Stored ISEE result for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error storing ISEE result for user {user_id}: {str(e)}")
        raise

async def validate_family_members(members_text: str) -> Optional[int]:
    """Validate family members input."""
    try:
        members = int(members_text)
        if not 1 <= members <= 20:
            raise ValueError("Family members must be between 1 and 20.")
        return members
    except ValueError:
        return None

async def validate_annual_income(income_text: str) -> Optional[float]:
    """Validate annual income input."""
    try:
        income = float(income_text)
        if income < 0:
            raise ValueError("Annual income cannot be negative.")
        return income
    except ValueError:
        return None

async def validate_property_area(area_text: str) -> Optional[float]:
    """Validate property area input."""
    try:
        area = float(area_text)
        if area < 0:
            raise ValueError("Property area cannot be negative.")
        return area
    except ValueError:
        return None

async def start_isee_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the ISEE calculation process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    logger.info(f"📊 ISEE calculation started by user {user_id}")
    
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("family_members_prompt", lang)),
            parse_mode="MarkdownV2"
        )
        return FAMILY_MEMBERS
    except TelegramError as e:
        logger.error(f"❌ Telegram error starting ISEE calculation for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def family_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle family members input."""
    lang = context.user_data.get("lang", "en")
    members_text = update.message.text.strip()
    members = await validate_family_members(members_text)
    
    if members is None:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_family_members", lang)),
            parse_mode="MarkdownV2"
        )
        return FAMILY_MEMBERS
    
    context.user_data["family_members"] = members
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("annual_income_prompt", lang)),
            parse_mode="MarkdownV2"
        )
        return ANNUAL_INCOME
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {update.effective_user.id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def annual_income(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle annual income input."""
    lang = context.user_data.get("lang", "en")
    income_text = update.message.text.strip()
    income = await validate_annual_income(income_text)
    
    if income is None:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_annual_income", lang)),
            parse_mode="MarkdownV2"
        )
        return ANNUAL_INCOME
    
    context.user_data["annual_income"] = income
    try:
        keyboard = [
            [
                InlineKeyboardButton(get_translated_text("yes", lang), callback_data="owner_yes"),
                InlineKeyboardButton(get_translated_text("no", lang), callback_data="owner_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("is_owner_prompt", lang)),
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        return IS_OWNER
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {update.effective_user.id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def is_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle property ownership input."""
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "en")
    choice = query.data.split("_")[1]
    
    try:
        if choice == "yes":
            await query.message.reply_text(
                sanitize_markdown(get_translated_text("property_area_prompt", lang)),
                parse_mode="MarkdownV2",
                reply_markup=ReplyKeyboardRemove()
            )
            return PROPERTY_AREA
        else:
            return await calculate_and_send_result(update, context, property_value=0)
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {update.effective_user.id}: {str(e)}")
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def property_area(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle property area input."""
    lang = context.user_data.get("lang", "en")
    area_text = update.message.text.strip()
    area = await validate_property_area(area_text)
    
    if area is None:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_property_area", lang)),
            parse_mode="MarkdownV2"
        )
        return PROPERTY_AREA
    
    property_value = area * PROPERTY_VALUE_FACTOR * PROPERTY_VALUE_MULTIPLIER
    return await calculate_and_send_result(update, context, property_value)

async def calculate_and_send_result(update: Update, context: ContextTypes.DEFAULT_TYPE, property_value: float) -> int:
    """Calculate ISEE, store result, and send to user."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    income = context.user_data["annual_income"]
    members = context.user_data["family_members"]
    
    try:
        coefficient = ISEE_COEFFICIENTS.get(members, max(ISEE_COEFFICIENTS.values()))
        isee = (income + property_value) / coefficient
        status = get_scholarship_status(isee, lang)
        
        # Store result in database using ORM
        await store_isee_result(user_id, members, income, property_value, isee, status)
        
        # Store in Google Sheets (StudentBotQuestions)
        user = await get_user(user_id)
        if user:
            isee_data = [
                user_id,
                user.first_name,
                user.last_name or "N/A",
                user.age or 0,
                user.email or "N/A",
                user.field_of_study or "N/A",
                user.country or "N/A",
                f"ISEE Calculation: {isee:.2f}",
                f"Status: {status}, Members: {members}, Income: {income}, Property: {property_value}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            ]
            await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, isee_data)
        
        # Award points for ISEE calculation
        await award_points_for_action(user_id, "isee_calculation")
        await log_event(user_id, "isee_calculated", f"ISEE: {isee:.2f}, Status: {status}")
        
        # Send result to user
        message = f"""📊 *ISEE:* {isee:.2f}\n{status}"""
        await update.message.reply_text(
            message,
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        logger.info(f"✅ ISEE calculated: {isee:.2f} for user {user_id}")
        
        # Clear user_data
        context.user_data.clear()
        context.user_data["lang"] = lang  # Preserve language
        return ConversationHandler.END
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error sending ISEE result for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Unexpected error calculating ISEE for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

def get_scholarship_status(isee: float, lang: str) -> str:
    """Determine scholarship status based on ISEE value."""
    if isee <= SCHOLARSHIP_THRESHOLDS["full"]:
        return get_translated_text("scholarship_status_full", lang)
    elif isee <= SCHOLARSHIP_THRESHOLDS["medium"]:
        return get_translated_text("scholarship_status_medium", lang)
    elif isee <= SCHOLARSHIP_THRESHOLDS["partial"]:
        return get_translated_text("scholarship_status_partial", lang)
    else:
        return get_translated_text("scholarship_status_none", lang)

async def cancel_isee_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the ISEE calculation process."""
    lang = context.user_data.get("lang", "en")
    user_id = update.effective_user.id
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("isee_calculation_cancelled", lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        context.user_data["lang"] = lang  # Preserve language
        logger.info(f"✅ ISEE calculation cancelled by user {user_id}")
        return ConversationHandler.END
    except TelegramError as e:
        logger.error(f"❌ Telegram error cancelling ISEE calculation for user {user_id}: {str(e)}")
        return ConversationHandler.END

def get_isee_handler():
    """Return the ISEE calculation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler("isee", start_isee_calculation)],
        states={
            FAMILY_MEMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, family_members)],
            ANNUAL_INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, annual_income)],
            IS_OWNER: [CallbackQueryHandler(is_owner, pattern="^owner_")],
            PROPERTY_AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, property_area)],
        },
        fallbacks=[CommandHandler("cancel", cancel_isee_calculation)],
    )
