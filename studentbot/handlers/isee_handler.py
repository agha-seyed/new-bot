import logging
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.constants import ParseMode
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from studentbot.utils.text_formatter import get_translated_text

logger = logging.getLogger(__name__)

# States
FAMILY_MEMBERS, ANNUAL_INCOME, IS_OWNER, PROPERTY_AREA = range(4)

async def start_isee_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    logger.info(f"ISEE calculation started by user {update.effective_user.id}")
    await update.message.reply_text(get_translated_text("family_members_prompt", lang))
    return FAMILY_MEMBERS

async def family_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        value = int(update.message.text)
        if value <= 0 or value > 10:
            raise ValueError
        context.user_data["family_members"] = value
    except ValueError:
        await update.message.reply_text(get_translated_text("invalid_input", context.user_data.get("lang", "en")))
        return FAMILY_MEMBERS

    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("annual_income_prompt", lang))
    return ANNUAL_INCOME

async def annual_income(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        income = float(update.message.text)
        if income < 0:
            raise ValueError
        context.user_data["annual_income"] = income
    except ValueError:
        await update.message.reply_text(get_translated_text("invalid_input", context.user_data.get("lang", "en")))
        return ANNUAL_INCOME

    lang = context.user_data.get("lang", "en")
    keyboard = [[get_translated_text("yes", lang), get_translated_text("no", lang)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(get_translated_text("is_owner_prompt", lang), reply_markup=reply_markup)
    return IS_OWNER

async def is_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    text = update.message.text.lower()
    if text == get_translated_text("yes", lang).lower():
        await update.message.reply_text(get_translated_text("property_area_prompt", lang))
        return PROPERTY_AREA
    else:
        return await calculate_and_send_result(update, context, property_value=0)

async def property_area(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        area = float(update.message.text)
        if area < 0:
            raise ValueError
        property_value = area * 500 * 0.2  # ثابت‌ها قابل تنظیم هستند
    except ValueError:
        await update.message.reply_text(get_translated_text("invalid_input", context.user_data.get("lang", "en")))
        return PROPERTY_AREA

    return await calculate_and_send_result(update, context, property_value)

async def calculate_and_send_result(update: Update, context: ContextTypes.DEFAULT_TYPE, property_value: float) -> int:
    lang = context.user_data.get("lang", "en")
    income = context.user_data["annual_income"]
    members = context.user_data["family_members"]
    coefficient = {1: 1, 2: 1.57, 3: 2.04, 4: 2.46, 5: 2.85}.get(members, 2.85)
    isee = (income + property_value) / coefficient
    status = get_scholarship_status(isee, lang)

    await update.message.reply_text(
        f"*ISEE:* {isee:.2f}\n{status}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=ReplyKeyboardRemove()
    )
    logger.info(f"ISEE calculated: {isee:.2f} for user {update.effective_user.id}")
    return ConversationHandler.END

def get_scholarship_status(isee: float, lang: str) -> str:
    if isee <= 12650:
        return get_translated_text("scholarship_status_full", lang)
    elif isee <= 16445:
        return get_translated_text("scholarship_status_medium", lang)
    elif isee <= 23000:
        return get_translated_text("scholarship_status_partial", lang)
    else:
        return get_translated_text("scholarship_status_none", lang)

async def cancel_isee_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("isee_calculation_cancelled", lang), reply_markup=ReplyKeyboardRemove())
    logger.info(f"ISEE calculation cancelled by {update.effective_user.id}")
    return ConversationHandler.END

def get_isee_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("isee", start_isee_calculation)],
        states={
            FAMILY_MEMBERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, family_members)],
            ANNUAL_INCOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, annual_income)],
            IS_OWNER: [MessageHandler(filters.TEXT & ~filters.COMMAND, is_owner)],
            PROPERTY_AREA: [MessageHandler(filters.TEXT & ~filters.COMMAND, property_area)],
        },
        fallbacks=[CommandHandler("cancel", cancel_isee_calculation)],
    )
