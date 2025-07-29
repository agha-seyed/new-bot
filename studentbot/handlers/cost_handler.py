import os
import json
import logging
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

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# States
RENT, FOOD, TRANSPORTATION, COMPARE_CITY = range(4)

# Load cost of living data
try:
    with open("studentbot/cost_of_living.json", "r", encoding="utf-8") as f:
        cost_of_living_data = json.load(f)
except Exception as e:
    logger.error(f"Failed to load cost_of_living.json: {e}")
    cost_of_living_data = {}


async def start_cost_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("rent_prompt", lang))
    return RENT


async def rent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["rent"] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter a valid number for rent.")
        return RENT
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("food_prompt", lang))
    return FOOD


async def food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["food"] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter a valid number for food.")
        return FOOD
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("transportation_prompt", lang))
    return TRANSPORTATION


async def transportation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        context.user_data["transportation"] = float(update.message.text)
    except ValueError:
        await update.message.reply_text("Please enter a valid number for transportation.")
        return TRANSPORTATION
    lang = context.user_data.get("lang", "en")
    cities = list(cost_of_living_data.keys())
    keyboard = [cities[i:i + 2] for i in range(0, len(cities), 2)]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text(
        get_translated_text("compare_city_prompt", lang), reply_markup=reply_markup
    )
    return COMPARE_CITY


async def compare_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    city_to_compare = update.message.text.strip()

    if city_to_compare not in cost_of_living_data:
        await update.message.reply_text(get_translated_text("invalid_city", lang))
        return COMPARE_CITY

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
🧮 *{get_translated_text("your_total_cost", lang)}*: `{user_total:.2f}`
🏙️ *{get_translated_text("total_cost_in", lang)} {city_to_compare}*: `{city_total:.2f}`
    """
    await update.message.reply_text(comparison_text, parse_mode="Markdown")
    return ConversationHandler.END


async def cancel_cost_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    lang = context.user_data.get("lang", "en")
    await update.message.reply_text(get_translated_text("cost_calculation_cancelled", lang))
    return ConversationHandler.END


async def exchange_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    lang = context.user_data.get("lang", "en")
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")

    if not api_key:
        await update.message.reply_text("API key not set.")
        logger.error("EXCHANGE_RATE_API_KEY not found.")
        return

    try:
        url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/EUR"
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()
        exchange_rate = data["conversion_rates"]["IRR"]
        text = f"*{get_translated_text('cost_of_living_in_italy', lang)}*\n\n1 EUR = {exchange_rate} IRR"
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        logger.exception("Failed to fetch exchange rate.")
        await update.message.reply_text("Unable to fetch exchange rate at the moment.")


def get_cost_handler():
    return [
        ConversationHandler(
            entry_points=[CommandHandler("cost", start_cost_calculation)],
            states={
                RENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, rent)],
                FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, food)],
                TRANSPORTATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, transportation)],
                COMPARE_CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, compare_city)],
            },
            fallbacks=[CommandHandler("cancel", cancel_cost_calculation)],
        ),
        CommandHandler("exchange_rate", exchange_rate),
    ]
