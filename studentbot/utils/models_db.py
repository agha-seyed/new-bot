import logging
from typing import Optional
from datetime import datetime
import json
from pathlib import Path
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
import httpx
from studentbot.utils.common import get_translated_text, sanitize_markdown
from studentbot.utils.db_utils import AsyncSessionLocal, get_user, log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot.utils.models_db import CostCalculation
from studentbot import config

logger = logging.getLogger(__name__)

# States
RENT, FOOD, TRANSPORTATION, COMPARE_CITY = range(4)

# Simple in-memory cache for exchange rates
exchange_rate_cache = {}
EXCHANGE_RATE_CACHE_TTL = 3600  # 1 hour in seconds

# Load cost of living data
try:
    cost_data_path = Path(__file__).resolve().parent.parent / "cost_of_living.json"
    with open(cost_data_path, "r", encoding="utf-8") as f:
        cost_of_living_data = json.load(f).get("cities", {})
except Exception as e:
    logger.error(f"❌ Failed to load cost_of_living.json: {str(e)}")
    cost_of_living_data = {}

async def store_cost_calculation(
    user_id: int, rent: float, food: float, transportation: float, 
    compared_city: str, user_total: float, city_total: float
) -> None:
    """Store cost calculation in the database using ORM."""
    try:
        async with AsyncSessionLocal() as session:
            async with session.begin():
                cost_calc = CostCalculation(
                    user_id=user_id,
                    rent=rent,
                    food=food,
                    transportation=transportation,
                    compared_city=compared_city,
                    user_total=user_total,
                    city_total=city_total,
                    created_at=datetime.utcnow()
                )
                session.add(cost_calc)
                await session.commit()
                logger.info(f"✅ Stored cost calculation for user {user_id}")
    except Exception as e:
        logger.error(f"❌ Error storing cost calculation for user {user_id}: {str(e)}")
        raise

async def validate_number(text: str) -> Optional[float]:
    """Validate numeric input."""
    try:
        value = float(text.replace(",", "."))
        if value < 0:
            raise ValueError("Negative value")
        return value
    except ValueError:
        return None

async def start_cost_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start the cost of living calculation process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("rent_prompt", lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        logger.info(f"🧮 User {user_id} started cost calculation")
        await award_points_for_action(user_id, "interaction")
        return RENT
    except TelegramError as e:
        logger.error(f"❌ Telegram error starting cost calculation for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

async def rent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle rent input."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    rent_text = update.message.text.strip()
    
    rent = await validate_number(rent_text)
    if rent is None:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_number", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Invalid rent input by user {user_id}: {rent_text}")
        return RENT
    
    context.user_data["rent"] = rent
    await update.message.reply_text(
        sanitize_markdown(get_translated_text("food_prompt", lang)),
        parse_mode="MarkdownV2"
    )
    logger.info(f"🏠 User {user_id} entered rent: {rent}")
    return FOOD

async def food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle food cost input."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    food_text = update.message.text.strip()
    
    food = await validate_number(food_text)
    if food is None:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_number", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Invalid food cost input by user {user_id}: {food_text}")
        return FOOD
    
    context.user_data["food"] = food
    await update.message.reply_text(
        sanitize_markdown(get_translated_text("transportation_prompt", lang)),
        parse_mode="MarkdownV2"
    )
    logger.info(f"🍽️ User {user_id} entered food cost: {food}")
    return TRANSPORTATION

async def transportation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle transportation cost input."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    transportation_text = update.message.text.strip()
    
    transportation = await validate_number(transportation_text)
    if transportation is None:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("invalid_number", lang)),
            parse_mode="MarkdownV2"
        )
        logger.warning(f"⚠️ Invalid transportation cost input by user {user_id}: {transportation_text}")
        return TRANSPORTATION
    
    context.user_data["transportation"] = transportation
    cities = [(city["name"][lang], key) for key, city in cost_of_living_data.items()]
    keyboard = [
        [InlineKeyboardButton(city_name, callback_data=f"city_{city_key}")]
        for city_name, city_key in cities
    ]
    keyboard.append([
        InlineKeyboardButton(
            get_translated_text("back_to_main", lang),
            callback_data="back_to_main"
        )
    ])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        sanitize_markdown(get_translated_text("compare_city_prompt", lang)),
        parse_mode="MarkdownV2",
        reply_markup=reply_markup
    )
    logger.info(f"🚍 User {user_id} entered transportation cost: {transportation}")
    return COMPARE_CITY

async def compare_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Compare user's costs with a selected city."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        if query.data == "back_to_main":
            await query.message.reply_text(
                sanitize_markdown(get_translated_text("back_to_main", lang)),
                parse_mode="MarkdownV2"
            )
            logger.info(f"✅ User {user_id} returned to main menu")
            context.user_data.clear()
            context.user_data["lang"] = lang
            return ConversationHandler.END

        city_key = query.data.split("_", 1)[1]
        if city_key not in cost_of_living_data:
            await query.message.reply_text(
                sanitize_markdown(get_translated_text("invalid_city", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ Invalid city selected by user {user_id}: {city_key}")
            return COMPARE_CITY
        
        city_to_compare = cost_of_living_data[city_key]["name"][lang]
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
        
        # Store in database
        await store_cost_calculation(
            user_id=user_id,
            rent=context.user_data["rent"],
            food=context.user_data["food"],
            transportation=context.user_data["transportation"],
            compared_city=city_to_compare,
            user_total=user_total,
            city_total=city_total
        )
        
        # Prepare response
        comparison_text = f"""
🧮 *{sanitize_markdown(get_translated_text("your_total_cost", lang))}*: `{user_total:.2f} EUR`
🏙️ *{sanitize_markdown(get_translated_text("total_cost_in", lang))} {sanitize_markdown(city_to_compare)}*: `{city_total:.2f} EUR`
📝 *{sanitize_markdown(get_translated_text("details", lang))}*:
- 🏠 *{sanitize_markdown(get_translated_text("rent", lang))}*: {sanitize_markdown(cost_of_living_data[city_key]["rent"]["description"][lang])}
- 🍽️ *{sanitize_markdown(get_translated_text("food", lang))}*: {sanitize_markdown(cost_of_living_data[city_key]["food"]["description"][lang])}
- 🚍 *{sanitize_markdown(get_translated_text("transportation", lang))}*: {sanitize_markdown(cost_of_living_data[city_key]["transportation"]["description"][lang])}
"""
        # Reply markup for retry or back
        keyboard = [
            [
                InlineKeyboardButton(
                    get_translated_text("recalculate", lang),
                    callback_data="start_cost_calculation"
                ),
                InlineKeyboardButton(
                    get_translated_text("back_to_main", lang),
                    callback_data="back_to_main"
                ),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Store in Google Sheets
        async with AsyncSessionLocal() as session:
            user = await get_user(session, user_id)
            if user:
                interaction_data = [
                    user_id,
                    user.first_name,
                    user.last_name or "N/A",
                    user.age or 0,
                    user.email or "N/A",
                    user.field_of_study or "N/A",
                    user.country or "N/A",
                    "Cost Calculation",
                    f"Compared with {city_to_compare}: User={user_total:.2f}, City={city_total:.2f}",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
                await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await query.message.reply_text(
            comparison_text,
            parse_mode="MarkdownV2",
            reply_markup=reply_markup
        )
        await award_points_for_action(user_id, "cost_calculation")
        await log_event(user_id, "cost_calculated", f"Compared with {city_to_compare}: User={user_total:.2f}, City={city_total:.2f}")
        logger.info(f"✅ User {user_id} compared costs with {city_to_compare}")
        
        context.user_data.clear()
        context.user_data["lang"] = lang
        return ConversationHandler.END
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error comparing costs for user {user_id}: {str(e)}")
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"❌ Unexpected error comparing costs for user {user_id}: {str(e)}")
        await query.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
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
        # Check cache
        cache_key = "exchange_rate:EUR_IRR"
        cached = exchange_rate_cache.get(cache_key)
        if cached and (datetime.utcnow().timestamp() - cached["timestamp"]) < EXCHANGE_RATE_CACHE_TTL:
            exchange_rate = cached["rate"]
            logger.info(f"✅ Exchange rate retrieved from cache for user {user_id}: 1 EUR = {exchange_rate} IRR")
        else:
            async with httpx.AsyncClient() as client:
                url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/EUR"
                response = await client.get(url, timeout=10)
                response.raise_for_status()
                data = response.json()
                exchange_rate = data["conversion_rates"].get("IRR")
                if not exchange_rate:
                    raise ValueError("IRR rate not found")
                exchange_rate_cache[cache_key] = {
                    "rate": exchange_rate,
                    "timestamp": datetime.utcnow().timestamp()
                }
                logger.info(f"✅ Fetched exchange rate for user {user_id}: 1 EUR = {exchange_rate} IRR")
        
        text = f"""
🌍 *{sanitize_markdown(get_translated_text("cost_of_living_in_italy", lang))}*
💸 *1 EUR* = `{exchange_rate:.2f} IRR`
"""
        async with AsyncSessionLocal() as session:
            user = await get_user(session, user_id)
            if user:
                interaction_data = [
                    user_id,
                    user.first_name,
                    user.last_name or "N/A",
                    user.age or 0,
                    user.email or "N/A",
                    user.field_of_study or "N/A",
                    user.country or "N/A",
                    "Exchange Rate",
                    f"1 EUR = {exchange_rate:.2f} IRR",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
                await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await update.message.reply_text(text, parse_mode="MarkdownV2")
        await award_points_for_action(user_id, "interaction")
        await log_event(user_id, "exchange_rate_fetched", f"1 EUR = {exchange_rate:.2f} IRR")
        logger.info(f"✅ User {user_id} fetched exchange rate: 1 EUR = {exchange_rate} IRR")
    
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

async def cancel_cost_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the cost calculation process."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("cost_calculation_cancelled", lang)),
            parse_mode="MarkdownV2",
            reply_markup=ReplyKeyboardRemove()
        )
        context.user_data.clear()
        context.user_data["lang"] = lang
        logger.info(f"✅ User {user_id} cancelled cost calculation")
        return ConversationHandler.END
    except TelegramError as e:
        logger.error(f"❌ Telegram error cancelling cost calculation for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
        return ConversationHandler.END

def get_cost_handler():
    """Return the cost calculation and exchange rate handlers."""
    return [
        ConversationHandler(
            entry_points=[
                CommandHandler("cost", start_cost_calculation),
                CallbackQueryHandler(start_cost_calculation, pattern="^start_cost_calculation$")
            ],
            states={
                RENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, rent)],
                FOOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, food)],
                TRANSPORTATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, transportation)],
                COMPARE_CITY: [CallbackQueryHandler(compare_city, pattern="^city_|^back_to_main$")],
            },
            fallbacks=[CommandHandler("cancel", cancel_cost_calculation)],
        ),
        CommandHandler("exchange_rate", exchange_rate),
    ]
