import os
import logging
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
from studentbot.utils.text_formatter import get_translated_text, sanitize_markdown
from studentbot.utils.gsheets import gsheets_client
from studentbot.utils.db_utils import get_user, AsyncSessionLocal
from studentbot import config

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


async def notify_admin_unanswered(question: str, user_id: int, lang: str = "en") -> None:
    """Notifies the admin about an unanswered question, including timestamp and user details."""
    try:
        bot = Bot(token=config.TELEGRAM_TOKEN)
        admin_chat_id = config.ADMIN_CHAT_ID
        if not admin_chat_id:
            logger.warning("⚠️ ADMIN_CHAT_ID is not set.")
            return

        # Get user details
        async with AsyncSessionLocal() as session:
            user = await get_user(session, user_id)
            user_name = f"{user.first_name} {user.last_name}" if user else "Unknown User"

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        message = f"""
⚠️ *{sanitize_markdown(get_translated_text('unanswered_question_alert', lang))}*
👤 *{sanitize_markdown(get_translated_text('user', lang))}*: {sanitize_markdown(user_name)} (ID: `{user_id}`)
📅 *{sanitize_markdown(get_translated_text('time', lang))}*: `{timestamp}`
❓ *{sanitize_markdown(get_translated_text('question', lang))}*:
{sanitize_markdown(question)}
        """

        await bot.send_message(
            chat_id=admin_chat_id,
            text=message.strip(),
            parse_mode="MarkdownV2"
        )
        logger.info(f"✅ Notified admin about unanswered question from user {user_id}: {question}")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id,
                question,
                "N/A",
                0,
                "N/A",
                "N/A",
                "N/A",
                "Unanswered Question",
                f"Notified admin about unanswered question",
                timestamp
            ]
        )
    except TelegramError as e:
        logger.error(f"❌ Telegram error notifying admin for user {user_id}: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Unexpected error notifying admin for user {user_id}: {str(e)}")