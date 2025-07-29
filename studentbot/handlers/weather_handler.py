import os
import httpx
from telegram import Update
from telegram.ext import ContextTypes

from studentbot.utils.text_formatter import get_translated_text


def get_weather_emoji(condition: str) -> str:
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
    lang = context.user_data.get("lang", "en")
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")

    if not api_key:
        await update.message.reply_text("⚠️ Weather API key is missing. Please set OPENWEATHERMAP_API_KEY.")
        return

    lat = 43.1122
    lon = 12.3884
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        condition = data["weather"][0]["main"]
        emoji = get_weather_emoji(condition)

        weather_text = f"*{get_translated_text('weather_in_perugia', lang)}*\n\n"
        weather_text += f"{get_translated_text('weather', lang)}: {condition} {emoji}\n"
        weather_text += f"{get_translated_text('temperature', lang)}: {data['main']['temp']}°C\n"
        weather_text += f"{get_translated_text('humidity', lang)}: {data['main']['humidity']}%\n"

        await update.message.reply_text(weather_text, parse_mode="Markdown")

    except httpx.HTTPError as e:
        print(f"Weather API error: {e}")
        await update.message.reply_text(get_translated_text("weather_error", lang))
