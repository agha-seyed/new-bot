import os
import logging
from datetime import datetime, timedelta
from telegram import Bot
from sqlalchemy import text
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .db_utils import AsyncSessionLocal
from .text_formatter import get_translated_text

logger = logging.getLogger(__name__)

# 🧠 پیام‌های تشویقی برای کاربران غیرفعال
REMINDER_MESSAGES = [
    "سلام {name} عزیز! این هفته فعالیتی ازت ندیدیم... همه چی خوبه؟ بیا دوباره سری به بات بزن! 🤗",
    "🌱 {name} جان! ما دلمون برایت تنگ شده! فعالیتت خیلی برامون مهمه. بیا یه سر بزن بهمون!",
    "🎯 هی {name}! می‌دونستی با هر فعالیت امتیاز می‌گیری؟ این هفته جا موندی... بزن بریم! 💪",
    "📬 یه پیام خصوصی داری! ولی قبلش باید برگردی و فعال شی! 😉"
]

async def get_inactive_users():
    """کاربران غیرفعال ۷ روز گذشته را می‌گیرد."""
    async with AsyncSessionLocal() as session:
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        result = await session.execute(
            text("""
                SELECT id, first_name, last_name
                FROM users
                WHERE last_active IS NULL OR last_active < :seven_days_ago
            """),
            {"seven_days_ago": seven_days_ago}
        )
        return result.fetchall()

async def get_active_users():
    """کاربران فعال ۷ روز گذشته را می‌گیرد."""
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

async def send_weekly_report():
    """گزارش هفتگی به ادمین + پیام یادآوری به کاربران غیرفعال."""
    try:
        bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
        admin_chat_id = os.getenv("ADMIN_CHAT_ID")
        if not admin_chat_id:
            logger.warning("⚠️ ADMIN_CHAT_ID is not set.")
            return

        inactive_users = await get_inactive_users()
        active_users = await get_active_users()

        report_text = f"""📅 *Weekly Report*

✅ *Active Users (7d):* {len(active_users)}
❌ *Inactive Users (7d):* {len(inactive_users)}

🕒 *Time:* Sent every Monday at 10:00 AM
        """

        await bot.send_message(
            chat_id=admin_chat_id,
            text=report_text,
            parse_mode="Markdown"
        )
        logger.info("📨 Weekly admin report sent.")

        # ارسال پیام تشویقی به کاربران غیرفعال
        for user in inactive_users:
            user_id, first_name, _ = user
            message = get_random_message(first_name)
            try:
                await bot.send_message(chat_id=user_id, text=message)
                logger.info(f"✅ Reminder sent to {first_name} ({user_id})")
            except Exception as e:
                logger.warning(f"⚠️ Failed to message {user_id}: {e}")

    except Exception as e:
        logger.error(f"❌ Error in weekly report: {e}")

def get_random_message(name):
    """پیام تصادفی شخصی‌سازی‌شده بر اساس اسم کاربر."""
    import random
    template = random.choice(REMINDER_MESSAGES)
    return template.format(name=name or "دوست من")

def start_weekly_scheduler():
    """اضافه کردن به scheduler."""
    scheduler = AsyncIOScheduler()
    scheduler.add_job(send_weekly_report, "cron", day_of_week="mon", hour=10, minute=0)
    scheduler.start()
    logger.info("📆 Weekly scheduler started.")
