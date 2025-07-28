import feedparser
from telegram import Update
from telegram.ext import ContextTypes

from utils.text_formatter import get_translated_text


async def news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the latest news from the RSS feeds."""
    lang = context.user_data.get("lang", "en")
    news_feeds = {
        "en": "http://www.ansa.it/sito/notizie/mondo/mondo_rss.xml",
        "it": "http://www.ansa.it/sito/notizie/mondo/mondo_rss.xml",
        "fa": "https://www.irna.ir/rss",
    }
    feed = feedparser.parse(news_feeds[lang])
    news_text = f"*{get_translated_text('news', lang)}*\n\n"
    for entry in feed.entries[:5]:
        news_text += f"*{entry.title}*\n"
        news_text += f"{entry.summary}\n"
        news_text += f"{entry.link}\n\n"
    await update.message.reply_text(news_text, parse_mode="Markdown")
