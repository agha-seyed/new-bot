from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from utils.text_formatter import get_translated_text

# States
FAMILY_MEMBERS, ANNUAL_INCOME, IS_OWNER, PROPERTY_AREA = range(4)


async def start_isee_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the ISEE calculation conversation."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("family_members_prompt", lang))
    return FAMILY_MEMBERS


async def family_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the number of family members and asks for the annual income."""
    context.user_data["family_members"] = update.message.text
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("annual_income_prompt", lang))
    return ANNUAL_INCOME


async def annual_income(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the annual income and asks if the user is a property owner."""
    context.user_data["annual_income"] = update.message.text
    lang = context.user_data.get("lang", "en")
    keyboard = [[get_translated_text("yes", lang), get_translated_text("no", lang)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        get_translated_text("is_owner_prompt", lang), reply_markup=reply_markup
    )
    return IS_OWNER


async def is_owner(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the user's property ownership status and asks for the property area if they are an owner."""
    lang = context.user_data.get("lang", "en")
    if update.message.text == get_translated_text("yes", lang):
        await update.message.reply_text(get_translated_text("property_area_prompt", lang))
        return PROPERTY_AREA
    else:
        # Calculate ISEE
        annual_income = float(context.user_data["annual_income"])
        family_members = int(context.user_data["family_members"])
        household_coefficients = {1: 1, 2: 1.57, 3: 2.04, 4: 2.46, 5: 2.85}
        household_coefficient = household_coefficients.get(family_members, 2.85)
        isee = calculate_isee(annual_income, 0, household_coefficient)
        scholarship_status = get_scholarship_status(isee, lang)

        await update.message.reply_text(f"Your ISEE is: {isee:.2f}\n{scholarship_status}")
        return ConversationHandler.END


def calculate_isee(annual_income, property_value, household_coefficient):
    """Calculates the ISEE."""
    return (annual_income + property_value) / household_coefficient

def get_scholarship_status(isee, lang):
    """Determines the scholarship status based on the ISEE."""
    if isee <= 12650:
        return get_translated_text("scholarship_status_full", lang)
    elif isee <= 16445:
        return get_translated_text("scholarship_status_medium", lang)
    elif isee <= 23000:
        return get_translated_text("scholarship_status_partial", lang)
    else:
        return get_translated_text("scholarship_status_none", lang)

async def property_area(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the property area and calculates the ISEE."""
    context.user_data["property_area"] = update.message.text
    lang = context.user_data.get("lang", "en")

    # Calculate ISEE
    annual_income = float(context.user_data["annual_income"])
    property_area = float(context.user_data["property_area"])
    property_value = property_area * 500 * 0.2
    family_members = int(context.user_data["family_members"])
    household_coefficients = {1: 1, 2: 1.57, 3: 2.04, 4: 2.46, 5: 2.85}
    household_coefficient = household_coefficients.get(family_members, 2.85)
    isee = calculate_isee(annual_income, property_value, household_coefficient)
    scholarship_status = get_scholarship_status(isee, lang)

    await update.message.reply_text(f"Your ISEE is: {isee:.2f}\n{scholarship_status}")
    return ConversationHandler.END


async def cancel_isee_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("isee_calculation_cancelled", lang))
    return ConversationHandler.END


def get_isee_handler():
    """Returns the ISEE calculation conversation handler."""
    return ConversationHandler(
        entry_points=[CommandHandler("isee", start_isee_calculation)],
        states={
            FAMILY_MEMBERS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, family_members)
            ],
            ANNUAL_INCOME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, annual_income)
            ],
            IS_OWNER: [MessageHandler(filters.TEXT & ~filters.COMMAND, is_owner)],
            PROPERTY_AREA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, property_area)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_isee_calculation)],
    )
