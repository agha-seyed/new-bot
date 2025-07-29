import os
import logging
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .db_utils import get_all_users, get_all_consultation_requests

logger = logging.getLogger(__name__)


async def send_daily_report():
    """Sends a daily report to the admin."""
    try:
        bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if not admin_chat_id:
            logger.warning("⚠️ ADMIN_CHAT_ID is not set.")
            return

        users = await get_all_users()
        consultations = await get_all_consultation_requests()

        report_text = f"""📊 *Daily Report*

👤 *Total Users:* {len(users)}
📩 *Consultation Requests:* {len(consultations)}
🕒 *Time:* Sent automatically every midnight.
        """

        await bot.send_message(
            chat_id=admin_chat_id,
            text=report_text.strip(),
            parse_mode="Markdown"
        )
        logger.info("✅ Daily report sent successfully.")

    except Exception as e:
        logger.error(f"❌ Error sending daily report: {e}")


def start_scheduler():
    """Starts the scheduler."""
    try:
        scheduler = AsyncIOScheduler()
        scheduler.add_job(send_daily_report, "cron", hour=0, minute=0)
        scheduler.start()
        logger.info("🕓 Scheduler started for daily reports.")
    except Exception as e:
        logger.error(f"❌ Error starting scheduler: {e}")
