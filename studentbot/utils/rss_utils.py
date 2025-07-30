import logging
import feedparser
import asyncio
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


async def fetch_rss_articles(feed_url: str, max_items: int = 5) -> list:
    """Parses RSS feed and returns list of articles."""
    try:
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, feed_url)
        articles = []
        for entry in feed.entries[:max_items]:
            articles.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.summary if "summary" in entry else "",
                "published": entry.published if "published" in entry else "",
                "source": feed.feed.get("title", "Unknown")
            })
        logger.info(f"✅ Fetched {len(articles)} articles from RSS: {feed_url}")
        return articles
    except Exception as e:
        logger.error(f"❌ Error fetching RSS feed {feed_url}: {str(e)}")
        return []