import logging
import feedparser
from telegram import Update
from telegram.ext import ContextTypes

from studentbot.utils.text_formatter import get_translated_text

logger = logging.getLogger(__name__)

async def news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays the latest news from the RSS feeds."""
    lang = context.user_data.get("lang", "en")
    news_feeds = {
        "en": "http://www.ansa.it/sito/notizie/mondo/mondo_rss.xml",
        "it": "http://www.ansa.it/sito/notizie/mondo/mondo_rss.xml",
        "fa": "https://www.irna.ir/rss",
    }

    if lang not in news_feeds:
        lang = "en"

    try:
        feed = feedparser.parse(news_feeds[lang])
        if not feed.entries:
            raise ValueError("No news entries found.")

        news_text = f"*{get_translated_text('news', lang)}*\n\n"
        for entry in feed.entries[:5]:
            title = entry.title
            summary = entry.summary if hasattr(entry, "summary") else ""
            link = entry.link
            news_text += f"🔹 [{title}]({link})\n{summary}\n\n"

        await update.message.reply_text(news_text, parse_mode="Markdown")
        logger.info(f"Sent news to user {update.message.from_user.id} in language {lang}")

    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        await update.message.reply_text(get_translated_text("news_fetch_error", lang))
