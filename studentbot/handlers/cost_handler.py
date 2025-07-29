import json
import httpx
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from ..utils.text_formatter import get_translated_text

# States
RENT, FOOD, TRANSPORTATION, COMPARE_CITY = range(4)

# Load cost of living data
with open("studentbot/cost_of_living.json", "r", encoding="utf-8") as f:
    cost_of_living_data = json.load(f)


async def start_cost_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the cost of living calculation conversation."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("rent_prompt", lang))
    return RENT


async def rent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the rent and asks for the food costs."""
    context.user_data["rent"] = float(update.message.text)
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("food_prompt", lang))
    return FOOD


async def food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the food costs and asks for the transportation costs."""
    context.user_data["food"] = float(update.message.text)
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("transportation_prompt", lang))
    return TRANSPORTATION


async def transportation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the transportation costs and asks which city to compare to."""
    context.user_data["transportation"] = float(update.message.text)
    lang = context.user_data.get("lang", "en")
    cities = list(cost_of_living_data.keys())
    keyboard = [cities]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text(
        get_translated_text("compare_city_prompt", lang), reply_markup=reply_markup
    )
    return COMPARE_CITY


async def compare_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Compares the cost of living to another city and ends the conversation."""
    lang = context.user_data.get("lang", "en")
    city_to_compare = update.message.text
    user_total = (
        context.user_data["rent"]
        + context.user_data["food"]
        + context.user_data["transportation"]
    )
    city_total = (
        cost_of_living_data[city_to_compare]["rent"]
        + cost_of_living_data[city_to_compare]["food"]
        + cost_of_living_data[city_to_compare]["transportation"]
    )
    comparison_text = f"""
*Your Total Cost:* {user_total:.2f}
*Total Cost in {city_to_compare}:* {city_total:.2f}
    """
    await update.message.reply_text(comparison_text, parse_mode="Markdown")
    return ConversationHandler.END


async def cancel_cost_calculation(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Cancels and ends the conversation."""
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(
        get_translated_text("cost_calculation_cancelled", lang)
    )
    return ConversationHandler.END


async def exchange_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the current exchange rate between EUR and IRR."""
    lang = context.user_data.get("lang", "en")
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/EUR"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
    exchange_rate = data["conversion_rates"]["IRR"]
    cost_of_living_text = f"*{get_translated_text('cost_of_living_in_italy', lang)}*\n\n"
    cost_of_living_text += f"1 EUR = {exchange_rate} IRR"
    await update.message.reply_text(cost_of_living_text, parse_mode="Markdown")

def get_cost_handler():
    """Returns the cost of living calculation conversation handler."""
    return [
        ConversationHandler(
            entry_points=[CommandHandler("cost", start_cost_calculation)],
            states={
                RENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, rent)],
                FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, food)],
                TRANSPORTATION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, transportation)
                ],
                COMPARE_CITY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, compare_city)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel_cost_calculation)],
        ),
        CommandHandler("exchange_rate", exchange_rate),
    ]
