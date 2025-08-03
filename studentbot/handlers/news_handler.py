import logging
from typing import List, Dict
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import TelegramError
from studentbot.utils.common import get_translated_text, sanitize_markdown
from studentbot.utils.rss_utils import fetch_rss_articles
from studentbot import config

logger = logging.getLogger(__name__)

async def news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch and display the latest news from RSS feeds."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        # Fetch articles from configured RSS feeds
        articles = []
        for feed_url in config.RSS_FEED_URLS:
            feed_articles = await fetch_rss_articles(feed_url, max_items=5)
            articles.extend(feed_articles)
        
        if not articles:
            await update.message.reply_text(
                sanitize_markdown(get_translated_text("no_news_available", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ No articles fetched for user {user_id}")
            return
        
        # Sort articles by publication date (if available)
        articles.sort(key=lambda x: x.get("published", ""), reverse=True)
        
        # Prepare news message
        news_text = f"📰 *{sanitize_markdown(get_translated_text('latest_news', lang))}*\n\n"
        for i, article in enumerate(articles[:5], 1):
            title = sanitize_markdown(article["title"])
            source = sanitize_markdown(article["source"])
            summary = sanitize_markdown(article["summary"][:200] + "..." if len(article["summary"]) > 200 else article["summary"])
            news_text += f"{i}\\. *{title}* \\({source}\\)\n{summary}\n[{sanitize_markdown(get_translated_text('read_more', lang))}]({article['link']})\n\n"
        
        keyboard = [
            [InlineKeyboardButton(get_translated_text("refresh_news", lang), callback_data="refresh_news")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            news_text.strip(),
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
            reply_markup=reply_markup
        )
        logger.info(f"✅ Displayed news for user {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error displaying news for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error displaying news for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

async def refresh_news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Refresh the news feed upon user request."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        # Fetch fresh articles
        articles = []
        for feed_url in config.RSS_FEED_URLS:
            feed_articles = await fetch_rss_articles(feed_url, max_items=5)
            articles.extend(feed_articles)
        
        if not articles:
            await query.edit_message_text(
                sanitize_markdown(get_translated_text("no_news_available", lang)),
                parse_mode="MarkdownV2"
            )
            logger.warning(f"⚠️ No articles fetched for user {user_id} on refresh")
            return
        
        # Sort articles by publication date
        articles.sort(key=lambda x: x.get("published", ""), reverse=True)
        
        # Prepare refreshed news message
        news_text = f"📰 *{sanitize_markdown(get_translated_text('latest_news', lang))}*\n\n"
        for i, article in enumerate(articles[:5], 1):
            title = sanitize_markdown(article["title"])
            source = sanitize_markdown(article["source"])
            summary = sanitize_markdown(article["summary"][:200] + "..." if len(article["summary"]) > 200 else article["summary"])
            news_text += f"{i}\\. *{title}* \\({source}\\)\n{summary}\n[{sanitize_markdown(get_translated_text('read_more', lang))}]({article['link']})\n\n"
        
        keyboard = [
            [InlineKeyboardButton(get_translated_text("refresh_news", lang), callback_data="refresh_news")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            news_text.strip(),
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
            reply_markup=reply_markup
        )
        logger.info(f"✅ Refreshed news for user {user_id}")
    
    except TelegramError as e:
        logger.error(f"❌ Telegram error refreshing news for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error refreshing news for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )

def get_news_handler():
    """Return the news handler."""
    return [
        CommandHandler("news", news),
        CallbackQueryHandler(refresh_news, pattern="^refresh_news$")
    ]
