import os
import httpx
from telegram import Update
from telegram.ext import ContextTypes

from ..utils.text_formatter import get_translated_text


async def weather(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the current weather in Perugia."""
    lang = context.user_data.get("lang", "en")
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    lat = 43.1122
    lon = 12.3884
    url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={api_key}&units=metric"
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        data = response.json()
    weather_text = f"*{get_translated_text('weather_in_perugia', lang)}*\n\n"
    weather_text += f"{get_translated_text('weather', lang)}: {data['weather'][0]['main']}\n"
    weather_text += f"{get_translated_text('temperature', lang)}: {data['main']['temp']}°C\n"
    weather_text += f"{get_translated_text('humidity', lang)}: {data['main']['humidity']}%\n"
    await update.message.reply_text(weather_text, parse_mode="Markdown")
