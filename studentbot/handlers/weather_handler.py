import logging
from datetime import datetime
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from telegram.error import TelegramError
from studentbot.utils.common import get_translated_text, sanitize_markdown  # Changed from text_formatter
from studentbot.utils.db_utils import get_user, AsyncSessionLocal, log_event
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

logger = logging.getLogger(__name__)

def get_weather_emoji(condition: str) -> str:
    """Return emoji based on weather condition."""
    mapping = {
        "Clear": "☀️",
        "Clouds": "☁️",
        "Rain": "🌧️",
        "Drizzle": "🌦️",
        "Thunderstorm": "⛈️",
        "Snow": "❄️",
        "Mist": "🌫️",
        "Fog": "🌁",
        "Haze": "🌫️"
    }
    return mapping.get(condition, "🌡️")

async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display current weather in Perugia."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    api_key = config.OPENWEATHERMAP_API_KEY
    
    if not api_key:
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("api_key_missing", lang)),
            parse_mode="MarkdownV2"
        )
        logger.error(f"❌ Weather API key missing for user {user_id}")
        return

    lat = 43.1122
    lon = 12.3884
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

        condition = data["weather"][0]["main"]
        emoji = get_weather_emoji(condition)
        
        weather_text = f"""
*{sanitize_markdown(get_translated_text('weather_in_perugia', lang))}*
{emoji} *{sanitize_markdown(get_translated_text('weather', lang))}*: {sanitize_markdown(condition)}
🌡️ *{sanitize_markdown(get_translated_text('temperature', lang))}*: {data['main']['temp']}°C
💧 *{sanitize_markdown(get_translated_text('humidity', lang))}*: {data['main']['humidity']}%
💨 *{sanitize_markdown(get_translated_text('wind_speed', lang))}*: {data['wind']['speed']} m/s
        """
        
        keyboard = [[InlineKeyboardButton(get_translated_text("refresh_weather", lang), callback_data="refresh_weather")]]
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
                    "Weather Request",
                    f"Fetched weather for Perugia: {condition}, {data['main']['temp']}°C",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
                await gsheets_client.add_interaction_to_sheet(config.QUESTIONS_SHEET_NAME, interaction_data)
        
        await update.message.reply_text(
            weather_text.strip(),
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        await award_points_for_action(user_id, "interaction")
        async with AsyncSessionLocal() as session:
            await log_event(session, user_id, "weather_fetched", f"Fetched weather for Perugia: {condition}, {data['main']['temp']}°C")
        logger.info(f"✅ Weather displayed for user {user_id}")
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Weather API HTTP error for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("weather_error", lang)),
            parse_mode="MarkdownV2"
        )
    except httpx.RequestError as e:
        logger.error(f"❌ Weather API request error for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("weather_error", lang)),
            parse_mode="MarkdownV2"
        )
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying weather for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def weather_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle weather refresh callback."""
    query = update.callback_query
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await query.answer()
        if query.data == "refresh_weather":
            await weather(Update(query.from_user, query.message), context)
            async with AsyncSessionLocal() as session:
                await log_event(session, user_id, "weather_refreshed", "Refreshed weather for Perugia")
            logger.info(f"✅ User {user_id} refreshed weather")
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling weather callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

def get_weather_handler():
    """Return the weather handler."""
    return [
        CommandHandler("weather", weather),
        CallbackQueryHandler(weather_callback, pattern="^refresh_weather$")
    ]
