import os
from datetime import datetime
from telegram import Bot

async def notify_admin_unanswered(question: str, user_id: int) -> None:
    """Notifies the admin about an unanswered question, including timestamp."""
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")

    if not admin_chat_id:
        return  # No admin defined, skip notification

    # ثبت زمان به صورت YYYY-MM-DD HH:MM:SS
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # متن پیام ارسالی به ادمین
    message = (
        f"⚠️ *Unanswered Question Alert*\n\n"
        f"👤 User ID: `{user_id}`\n"
        f"📅 Time: `{timestamp}`\n\n"
        f"❓ *Question:*\n{question}"
    )

    await bot.send_message(
        chat_id=admin_chat_id,
        text=message,
        parse_mode="Markdown"
    )