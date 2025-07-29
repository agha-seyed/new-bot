import logging
from datetime import datetime
import feedparser
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action
from studentbot import config

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# RSS feeds for different languages
NEWS_FEEDS = {
    "en": "http://www.ansa.it/sito/notizie/mondo/mondo_rss.xml",
    "it": "http://www.ansa.it/sito/notizie/mondo/mondo_rss.xml",
    "fa": "https://www.irna.ir/rss",
}


async def news(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the latest news from RSS feeds with interactive buttons."""
    user_id = update.effective_user.id
    lang = context.user_data.get("lang", "en")
    
    if lang not in NEWS_FEEDS:
        lang = "en"

    try:
        feed = feedparser.parse(NEWS_FEEDS[lang])
        if not feed.entries:
            raise ValueError("No news entries found.")

        news_text = f"*{sanitize_markdown(get_translated_text('news', lang))}*\n\n"
        for entry in feed.entries[:5]:
            title = sanitize_markdown(entry.title)
            summary = sanitize_markdown(entry.summary) if hasattr(entry, "summary") else "No summary available"
            link = entry.link
            news_text += f"🔹 [{title}]({link})\n{summary}\n\n"

        keyboard = [[InlineKeyboardButton(get_translated_text("more_news", lang), callback_data="more_news")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            news_text,
            parse_mode="MarkdownV2",
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        logger.info(f"✅ Sent news to user {user_id} in language {lang}")
        await award_points_for_action(user_id, "interaction")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id,
                "N/A",
                "N/A",
                0,
                "N/A",
                "N/A",
                "N/A",
                "News Request",
                f"Fetched news in {lang}",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
    except ValueError as e:
        logger.error(f"❌ No news entries found for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("news_fetch_error", lang)),
            parse_mode="MarkdownV2"
        )
    except TelegramError as e:
        logger.error(f"❌ Telegram error sending news to user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )
    except Exception as e:
        logger.error(f"❌ Unexpected error fetching news for user {user_id}: {str(e)}")
        await update.message.reply_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )


async def news_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle news callback for more news."""
    query = update.callback_query
    user_id = query.from_user.id
    lang = context.user_data.get("lang", "en")
    
    try:
        await query.answer()
        if query.data == "more_news":
            feed = feedparser.parse(NEWS_FEEDS.get(lang, NEWS_FEEDS["en"]))
            if not feed.entries:
                raise ValueError("No news entries found.")

            news_text = f"*{sanitize_markdown(get_translated_text('more_news', lang))}*\n\n"
            for entry in feed.entries[5:10]:  # Next 5 news items
                title = sanitize_markdown(entry.title)
                summary = sanitize_markdown(entry.summary) if hasattr(entry, "summary") else "No summary available"
                link = entry.link
                news_text += f"🔹 [{title}]({link})\n{summary}\n\n"

            await query.edit_message_text(
                news_text,
                parse_mode="MarkdownV2",
                disable_web_page_preview=True
            )
            logger.info(f"✅ Sent more news to user {user_id} in language {lang}")
            await award_points_for_action(user_id, "interaction")
            await gsheets_client.add_interaction_to_sheet(
                config.QUESTIONS_SHEET_NAME,
                [
                    user_id,
                    "N/A",
                    "N/A",
                    0,
                    "N/A",
                    "N/A",
                    "N/A",
                    "More News Request",
                    f"Fetched more news in {lang}",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
            )
    except ValueError as e:
        logger.error(f"❌ No more news entries for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("news_fetch_error", lang)),
            parse_mode="MarkdownV2"
        )
    except TelegramError as e:
        logger.error(f"❌ Telegram error handling news callback for user {user_id}: {str(e)}")
        await query.edit_message_text(
            sanitize_markdown(get_translated_text("error_occurred", lang)),
            parse_mode="MarkdownV2"
        )


def get_news_handler():
    """Return the news handler."""
    return [
        CommandHandler("news", news),
        CallbackQueryHandler(news_callback, pattern="^more_news$"),
    ]