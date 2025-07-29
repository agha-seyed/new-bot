import feedparser

def fetch_rss_articles(feed_url: str, max_items: int = 5) -> list:
    """Parses RSS feed and returns list of articles."""
    feed = feedparser.parse(feed_url)
    articles = []
    for entry in feed.entries[:max_items]:
        articles.append({
            "title": entry.title,
            "link": entry.link,
            "summary": entry.summary if "summary" in entry else "",
            "published": entry.published if "published" in entry else "",
        })
    return articles
