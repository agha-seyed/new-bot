import logging
from typing import Optional
from datetime import datetime, timezone
import aiosmtplib
from email.message import EmailMessage
from studentbot import config
from studentbot.utils.gsheets import gsheets_client
from studentbot.utils.common import get_translated_text, sanitize_markdown
from studentbot.handlers.gamification_handler import award_points_for_action

logger = logging.getLogger(__name__)

MAX_EMAIL_BODY_LENGTH = 4000

async def send_email(to_email: str, subject: str, body: str, user_id: int, lang: str = "en") -> bool:
    """Send an email with the given subject and body asynchronously."""
    try:
        if not config.EMAIL_SENDER or not config.EMAIL_PASSWORD:
            logger.error("❌ EMAIL_SENDER or EMAIL_PASSWORD not set")
            return False

        msg = EmailMessage()
        msg["From"] = config.EMAIL_SENDER
        msg["To"] = to_email
        msg["Subject"] = sanitize_markdown(subject)
        msg.set_content(sanitize_markdown(body[:MAX_EMAIL_BODY_LENGTH]))

        await aiosmtplib.send(
            msg,
            hostname="smtp.gmail.com",
            port=465,
            username=config.EMAIL_SENDER,
            password=config.EMAIL_PASSWORD,
            use_tls=True
        )
        
        await award_points_for_action(user_id, "interaction")
        await gsheets_client.add_interaction_to_sheet(
            config.QUESTIONS_SHEET_NAME,
            [
                user_id, "N/A", body[:1000], 0, "N/A", to_email, "N/A",
                "Email Sent", f"Sent email to {to_email}",
                datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            ]
        )
        logger.info(f"✅ Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send email to {to_email}: {str(e)}")
        return False
