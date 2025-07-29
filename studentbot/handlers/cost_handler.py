import os
import json
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
from telegram.error import TelegramError
import httpx
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
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
RENT, FOOD, TRANSPORTATION, COMPARE_CITY = range(4)

# Load cost of living data
try:
    with open("studentbot/cost_of_living.json", "r", encoding="utf-8") as f:
        cost_of_living_data = json.load(f).get("cities", {})
except Exception as e:
    logger.error(f"❌ Failed to load cost_of_living.json: {str(e)}")
    cost_of_living_data = {}


async def start_cost_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the cost of living calculation process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("rent_prompt", lang)),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ User {user_id} started cost calculation")
        await award_points_for_action(user_id, "interaction")
        return RENT
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
        return ConversationHandler.END


async def rent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle rent input."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        rent = float(update.message.text.replace(",", "."))
        if rent < 0:
            raise ValueError("Negative value")
        context.user_data["rent"] = rent
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("food_prompt", lang)),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ User {user_id} entered rent: {rent}")
        return FOOD
    except ValueError:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_number", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Invalid rent input by user {user_id}: {update.message.text}")
        return RENT


async def food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle food cost input."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        food = float(update.message.text.replace(",", "."))
        if food < 0:
            raise ValueError("Negative value")
        context.user_data["food"] = food
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("transportation_prompt", lang)),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ User {user_id} entered food cost: {food}")
        return TRANSPORTATION
    except ValueError:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_number", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Invalid food cost input by user {user_id}: {update.message.text}")
        return FOOD


async def transportation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle transportation cost input."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        transportation = float(update.message.text.replace(",", "."))
        if transportation < 0:
            raise ValueError("Negative value")
        context.user_data["transportation"] = transportation
        cities = [city["name"][lang] for city in cost_of_living_data.values()]
        keyboard = [cities[i:i + 2] for i in range(0, len(cities), 2)]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("compare_city_prompt", lang)),
            reply_markup=reply_markup,
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ User {user_id} entered transportation cost: {transportation}")
        return COMPARE_CITY
    except ValueError:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_number", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Invalid transportation cost input by user {user_id}: {update.message.text}")
        return TRANSPORTATION


async def compare_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Compare user's costs with a selected city."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    city_to_compare = update.message.text.strip()
    
    try:
        # Find the city key that matches the translated name
        city_key = next(
            (key for key, value in cost_of_living_data.items() if value["name"][lang] == city_to_compare),
            None
        )
        if not city_key:
            await update.message.reply_text(
                sanitize_markdown(get_translated_text("invalid_city", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ Invalid city selected by user {user_id}: {city_to_compare}")
            return COMPARE_CITY

        user_total = (
            context.user_data["rent"]
            + context.user_data["food"]
            + context.user_data["transportation"]
        )
        city_total = (
            cost_of_living_data[city_key]["rent"]["value"]
            + cost_of_living_data[city_key]["food"]["value"]
            + cost_of_living_data[city_key]["transportation"]["value"]
        )
        comparison_text = f"""
🧮 *{sanitize_markdown(get_translated_text("your_total_cost", lang))}*: `{user_total:.2f} EUR`
🏙️ *{sanitize_markdown(get_translated_text("total_cost_in", lang))} {sanitize_markdown(city_to_compare)}*: `{city_total:.2f} EUR`
📝 *{sanitize_markdown(get_translated_text("details", lang))}*:
- 🏠 {sanitize_markdown(get_translated_text("rent", lang))}: {cost_of_living_data[city_key]["rent"]["description"][lang]}
- 🍽️ {sanitize_markdown(get_translated_text("food", lang))}: {cost_of_living_data[city_key]["food"]["description"][lang]}
- 🚍 {sanitize_markdown(get_translated_text("transportation", lang))}: {cost_of_living_data[city_key]["transportation"]["description"][lang]}
        """
        await update.message.reply_text(comparison_text, parse_mode="MarkdownV2")
        logger.info(f"✅ User {user_id} compared costs with {city_to_compare}")
        await award_points_for_action(user_id, "cost_calculation")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id,
                "N/A",
                "N/A",
                0,
                "N/A",
                "N/A",
                "N/A",
                "Cost Calculation",
                f"Compared with {city_to_compare}: User={user_total:.2f}, City={city_total:.2f}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
        return ConversationHandler.END
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Unexpected error for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
        return ConversationHandler.END


async def cancel_cost_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the cost calculation process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("cost_calculation_cancelled", lang)),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ User {user_id} cancelled cost calculation")
        return ConversationHandler.END
    except TelegramError as e:
        logger.error(f"❌ Telegram error for user {user_id}: {str(e)}")
        await update.message.reply_text(get_translated_text("error_occurred", lang))
        return ConversationHandler.END


async def exchange_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch and display exchange rate (EUR to IRR)."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    
    if not api_key:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("api_key_missing", lang)),
            parse_mode="MarkdownV2"
        )
        logger.error(f"❌ EXCHANGE_RATE_API_KEY not found for user {user_id}")
        return

    try:
        async with httpx.AsyncClient() as client:
            url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/EUR"
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
        
        exchange_rate = data["conversion_rates"].get("IRR", None)
        if not exchange_rate:
            raise ValueError("IRR rate not found")
        
        text = f"""
🌍 *{sanitize_markdown(get_translated_text("cost_of_living_in_italy", lang))}*
💸 *1 EUR* = `{exchange_rate:.2f} IRR`
        """
        await update.message.reply_text(text, parse_mode="MarkdownV2")
        logger.info(f"✅ User {user_id} fetched exchange rate: 1 EUR = {exchange_rate} IRR")
        await award_points_for_action(user_id, "interaction")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id,
                "N/A",
                "N/A",
                0,
                "N/A",
                "N/A",
                "N/A",
                "Exchange Rate",
                f"1 EUR = {exchange_rate:.2f} IRR",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP error fetching exchange rate for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("exchange_rate_failed", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching exchange rate for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("exchange_rate_failed", lang)),
            parse_mode="MarkdownV2"
        )


def get_cost_handler():
    """Return the cost calculation and exchange rate handlers."""
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