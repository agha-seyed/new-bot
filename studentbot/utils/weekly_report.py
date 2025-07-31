import logging
from telegram import Bot
from telegram.error import TelegramError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from sqlalchemy import text
from studentbot import config
from studentbot.utils.db_utils import get_all_consultation_requests, AsyncSessionLocal
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.gsheets import gsheets_client
from studentbot.handlers.gamification_handler import award_points_for_action

logger = logging.getLogger(__name__)

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

class Scheduler:
    """Manages scheduled tasks for the bot."""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    
    async def get_users_count(self) -> int:
        """Get total number of users."""
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
    
    async def get_inactive_users(self):
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
    
    async def get_active_users(self):
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
    
    async def send_daily_report(self):
        """Send a daily report to the admin."""
        if not config.ADMIN_CHAT_ID:
            logger.warning("⚠️ ADMIN_CHAT_ID is not set")
            return
        
        try:
            users_count = await self.get_users_count()
            new_users_count = await self.get_new_users_count()
            consultations = await get_all_consultation_requests()
            pending_consultations = len([c for c in consultations if c["status"] == "pending"])
            
            report_text = (
                f"📊 *Daily Report*\n\n"
                f"👤 *Total Users*: {users_count}\n"
                f"🆕 *New Users Today*: {new_users_count}\n"
                f"📩 *Total Consultation Requests*: {len(consultations)}\n"
                f"⏳ *Pending Consultations*: {pending_consultations}\n"
                f"🕒 *Time*: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
            await self.bot.send_message(
                chat_id=config.ADMIN_CHAT_ID,
                text=report_text.strip(),
                parse_mode="MarkdownV2"
            )
            logger.info("✅ Daily report sent")
        except TelegramError as e:
            logger.error(f"❌ Telegram error sending daily report: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Error sending daily report: {str(e)}")
    
    async def send_weekly_report(self):
        """Send weekly report to admin and reminders to inactive users."""
        try:
            admin_chat_id = config.ADMIN_CHAT_ID
            if not admin_chat_id:
                logger.warning("⚠️ ADMIN_CHAT_ID is not set")
                return

            inactive_users = await self.get_inactive_users()
            active_users = await self.get_active_users()

            report_text = (
                f"📅 *{sanitize_markdown(get_translated_text('weekly_report', 'en'))}*\n\n"
                f"✅ *{sanitize_markdown(get_translated_text('active_users', 'en'))}*: {len(active_users)}\n"
                f"❌ *{sanitize_markdown(get_translated_text('inactive_users', 'en'))}*: {len(inactive_users)}\n"
                f"🕒 *{sanitize_markdown(get_translated_text('time', 'en'))}*: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            await self.bot.send_message(
                chat_id=admin_chat_id,
                text=report_text.strip(),
                parse_mode="MarkdownV2"
            )
            logger.info("✅ Weekly admin report sent")
            await gsheets_client.add_interaction_to_sheet(
                config.QUESTIONS_SHEET_NAME,
                [
                    "N/A", "N/A", report_text[:1000], 0, "N/A", admin_chat_id, "N/A",
                    "Weekly Report", "Sent weekly report to admin",
                    datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                ]
            )

            for user in inactive_users:
                user_id, first_name, _, lang = user
                message = random.choice(REMINDER_MESSAGES.get(lang, REMINDER_MESSAGES["en"])).format(name=first_name or "Friend")
                try:
                    await self.bot.send_message(
                        chat_id=user_id,
                        text=sanitize_markdown(message),
                        parse_mode="MarkdownV2"
                    )
                    await award_points_for_action(user_id, "interaction")
                    logger.info(f"✅ Reminder sent to {first_name} ({user_id})")
                    await gsheets_client.add_interaction_to_sheet(
                        config.QUESTIONS_SHEET_NAME,
                        [
                            user_id, "N/A", message[:1000], 0, "N/A", "N/A", "N/A",
                            "Inactive User Reminder", f"Sent reminder to {first_name}",
                            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                        ]
                    )
                except TelegramError as e:
                    logger.warning(f"⚠️ Failed to message {user_id}: {str(e)}")

        except TelegramError as e:
            logger.error(f"❌ Telegram error in weekly report: {str(e)}")
        except Exception as e:
            logger.error(f"❌ Unexpected error in weekly report: {str(e)}")
    
    def start(self):
        """Start the scheduler."""
        try:
            self.scheduler.add_job(self.send_daily_report, "cron", hour=0, minute=0)
            self.scheduler.add_job(self.send_weekly_report, "cron", day_of_week="mon", hour=10, minute=0)
            self.scheduler.start()
            logger.info("🕓 Scheduler started for daily and weekly reports")
        except Exception as e:
            logger.error(f"❌ Error starting scheduler: {str(e)}")
            raise
    
    def shutdown(self):
        """Shutdown the scheduler."""
        try:
            self.scheduler.shutdown()
            logger.info("🛑 Scheduler stopped")
        except Exception as e:
            logger.error(f"❌ Error stopping scheduler: {str(e)}")

scheduler = Scheduler()
