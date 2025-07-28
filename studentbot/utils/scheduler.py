import os
from telegram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from utils.db_utils import get_all_users, get_all_consultation_requests


async def send_daily_report():
    """Sends a daily report to the admin."""
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")
    if admin_chat_id:
        num_users = len(get_all_users())
        num_consultation_requests = len(get_all_consultation_requests())
        report_text = f"""
*Daily Report*

*New Users:* {num_users}
*New Consultation Requests:* {num_consultation_requests}
        """
        await bot.send_message(
            chat_id=admin_chat_id, text=report_text, parse_mode="Markdown"
        )


def start_scheduler():
    """Starts the scheduler."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_daily_report, "cron", hour=0)
    scheduler.start()
