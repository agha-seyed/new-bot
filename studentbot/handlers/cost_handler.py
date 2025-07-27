import os
import requests
from telegram import Update
from telegram.ext import ContextTypes

from studentbot.utils.text_formatter import get_translated_text


async def cost_of_living(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the current exchange rate between EUR and IRR."""
    lang = context.user_data.get("lang", "en")
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    url = f"https://v6.exchangerate-api.com/v6/{api_key}/latest/EUR"
    response = requests.get(url)
    data = response.json()
    exchange_rate = data["conversion_rates"]["IRR"]
    cost_of_living_text = f"*{get_translated_text('cost_of_living_in_italy', lang)}*\n\n"
    cost_of_living_text += f"1 EUR = {exchange_rate} IRR"
    await update.message.reply_text(cost_of_living_text, parse_mode="Markdown")
