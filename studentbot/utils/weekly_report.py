import os
import logging
import random
from datetime import datetime, timedelta
from telegram import Bot
from telegram.error import TelegramError
from sqlalchemy import text
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from studentbot.utils.db_utils import AsyncSessionLocal
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

# Encouraging messages for inactive users
REMINDER_MESSAGES = {
    "en": [
        "Hi {name}! We missed you this week... Everything okay? Come back and explore! 🤗",
        "{name}, we’re waiting for you! Your activity means a lot to us. Drop by! 🌱",
        "Hey {name}! Did you know you earn points for every action? Don’t miss out this week! 💪",
        "📬 You’ve got a private message waiting! But first, come back and get active! 😉"
    ],
    "fa": [
        "سلام {name} عزیز! این هفته فعالیتی ازت ندیدیم... همه چی خوبه؟ بیا دوباره سری به بات بزن! 🤗",
        "{name} جان! ما دلمون برایت تنگ شده! فعالیتت خیلی برامون مهمه. بیا یه سر بزن بهمون! 🌱",
        "هی {name}! می‌دونستی با هر فعالیت امتیاز می‌گیری؟ این هفته جا موندی... بزن بریم! 💪",
        "📬 یه پیام خصوصی داری! ولی قبلش باید برگردی و فعال شی! 😉"
    ],
    "it": [
        "Ciao {name}! Ci sei mancato questa settimana... Tutto bene? Torna a trovarci! 🤗",
        "{name}, ti stiamo aspettando! La tua attività è importante per noi. Passa a trovarci! 🌱",
        "Ehi {name}! Lo sapevi che guadagni punti per ogni azione? Non perdere l’occasione! 💪",
        "📬 Hai un messaggio privato che ti aspetta! Ma prima, torna e diventa attivo! 😉"
    ]
}


async def get_inactive_users():
    """Fetch users inactive for the past 7 days."""
    try:
        async with AsyncSessionLocal() as session:
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            result = await session.execute(
                text("""
                    SELECT id, first_name, last_name, lang
                    FROM users
                    WHERE last_active IS NULL OR last_active < :seven_days_ago
                """),
                {"seven_days_ago": seven_days_ago}
            )
            return result.fetchall()
    except Exception as e:
        logger.error(f"❌ Error fetching inactive users: {str(e)}")
        return []


async def get_active_users():
    """Fetch users active in the past 7 days."""
    try:
        async with AsyncSessionLocal() as session:
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            result = await session.execute(
                text("""
                    SELECT id
                    FROM users
                    WHERE last_active >= :seven_days_ago
                """),
                {"seven_days_ago": seven_days_ago}
            )
            return result.fetchall()
    except Exception as e:
        logger.error(f"❌ Error fetching active users: {str(e)}")
        return []


async def send_weekly_report():
    """Send weekly report to admin and reminders to inactive users."""
    try:
        bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
        admin_chat_id = config.ADMIN_CHAT_ID
        if not admin_chat_id:
            logger.warning("⚠️ ADMIN_CHAT_ID is not set.")
            return

        inactive_users = await get_inactive_users()
        active_users = await get_active_users()

        report_text = f"""
📅 *{sanitize_markdown(get_translated_text('weekly_report', 'en'))}*
✅ *{sanitize_markdown(get_translated_text('active_users', 'en'))}*: {len(active_users)}
❌ *{sanitize_markdown(get_translated_text('inactive_users', 'en'))}*: {len(inactive_users)}
🕒 *{sanitize_markdown(get_translated_text('time', 'en'))}*: {datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}
        """

        await bot.send_message(
            chat_id=admin_chat_id,
            text=report_text.strip(),
            parse_mode="MarkdownV2"
        )
        logger.info("✅ Weekly admin report sent.")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                "N/A",
                "N/A",
                report_text[:1000],
                0,
                "N/A",
                admin_chat_id,
                "N/A",
                "Weekly Report",
                "Sent weekly report to admin",
                datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            ]
        )

        # Send reminders to inactive users
        for user in inactive_users:
            user_id, first_name, _, lang = user
            message = get_random_message(first_name, lang)
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=sanitize_markdown(message),
                    parse_mode="MarkdownV2"
                )
                await award_points_for_action(user_id, "interaction")
                logger.info(f"✅ Reminder sent to {first_name} ({user_id})")
                await gsheets_client.add_interaction_to_sheet(
                    config.QUESTIONS_SHEET_NAME,
                    [
                        user_id,
                        "N/A",
                        message[:1000],
                        0,
                        "N/A",
                        "N/A",
                        "N/A",
                        "Inactive User Reminder",
                        f"Sent reminder to {first_name}",
                        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                    ]
                )
            except TelegramError as e:
                logger.warning(f"⚠️ Failed to message {user_id}: {str(e)}")

    except TelegramError as e:
        logger.error(f"❌ Telegram error in weekly report: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Unexpected error in weekly report: {str(e)}")


def get_random_message(name: str, lang: str = "en") -> str:
    """Generate a random personalized message based on user name and language."""
    template = random.choice(REMINDER_MESSAGES.get(lang, REMINDER_MESSAGES["en"]))
    return template.format(name=name or "Friend")


def start_weekly_scheduler():
    """Start the weekly report scheduler."""
    try:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(send_weekly_report, "cron", day_of_week="mon", hour=10, minute=0)
        scheduler.start()
        logger.info("📆 Weekly scheduler started.")
    except Exception as e:
        logger.error(f"❌ Error starting weekly scheduler: {str(e)}")