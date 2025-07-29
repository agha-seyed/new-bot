import logging
from telegram import Bot
from telegram.error import TelegramError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import config
from studentbot.utils.db_utils import get_all_consultation_requests

logger = logging.getLogger(__name__)

class Scheduler:
    """Manages scheduled tasks for the bot."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    
    async def get_users_count(self) -> int:
        """Get total number of users (placeholder until get_all_users is implemented)."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(text("SELECT COUNT(*) FROM users"))
                return result.scalar_one_or_none() or 0
        except Exception as e:
            logger.error(f"❌ Error getting users count: {str(e)}")
            return 0
    
    async def get_new_users_count(self) -> int:
        """Get number of users registered today."""
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(
                    text("SELECT COUNT(*) FROM users WHERE DATE(created_at) = CURRENT_DATE")
                )
                return result.scalar_one_or_none() or 0
        except Exception as e:
            logger.error(f"❌ Error getting new users count: {str(e)}")
            return 0
    
    async def send_daily_report(self):
        """Send a daily report to the admin."""
        if not config.ADMIN_CHAT_ID:
            logger.warning("⚠️ ADMIN_CHAT_ID is not set. Skipping daily report.")
            return
        
        try:
            users_count = await self.get_users_count()
            new_users_count = await self.get_new_users_count()
            consultations = await get_all_consultation_requests()
            pending_consultations = len([c for c in consultations if c["status"] == "pending"])
            
            report_text = f"""📊 *Daily Report*

👤 *Total Users:* {users_count}
🆕 *New Users Today:* {new_users_count}
📩 *Total Consultation Requests:* {len(consultations)}
⏳ *Pending Consultations:* {pending_consultations}
🕒 *Time:* {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
            await self.bot.send_message(
                chat_id=config.ADMIN_CHAT_ID,
                text=report_text.strip(),
                parse_mode="MarkdownV2",
            )
            logger.info("✅ Daily report sent successfully.")
        except TelegramError as e:
            logger.error(f"❌ Telegram error sending daily report: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error sending daily report: {str(e)}")
    
    def start(self):
        """Start the scheduler."""
        try:
            self.scheduler.add_job(self.send_daily_report, "cron", hour=0, minute=0)
            self.scheduler.start()
            logger.info("🕓 Scheduler started for daily reports.")
        except Exception as e:
            logger.error(f"❌ Error starting scheduler: {str(e)}")
            raise
    
    def shutdown(self):
        """Shutdown the scheduler."""
        try:
            self.scheduler.shutdown()
            logger.info("🛑 Scheduler stopped.")
        except Exception as e:
            logger.error(f"❌ Error stopping scheduler: {str(e)}")

# Initialize scheduler
scheduler = Scheduler()