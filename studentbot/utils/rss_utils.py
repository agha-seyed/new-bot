import logging
from typing import List, Dict
import asyncio
import feedparser
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown

logger = logging.getLogger(__name__)

async def fetch_rss_articles(feed_url: str, max_items: int = 5) -> List[Dict[str, str]]:
    """Fetch and parse articles from an RSS feed."""
    try:
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, feedparser.parse, feed_url)
        articles = [
            {
                "title": entry.title,
                "link": entry.link,
                "summary": entry.summary if "summary" in entry else "",
                "published": entry.published if "published" in entry else "",
                "source": feed.feed.get("title", "Unknown")
            }
            for entry in feed.entries[:max_items]
        ]
        logger.info(f"✅ Fetched {len(articles)} articles from RSS: {feed_url}")
        return articles
    except Exception as e:
        logger.error(f"❌ Error fetching RSS feed {feed_url}: {str(e)}")
        return []
