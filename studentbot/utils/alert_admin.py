import os
from telegram import Bot

async def notify_admin_unanswered(question, user_id):
    """Notifies the admin about an unanswered question."""
    bot = Bot(token=os.getenv("TELEGRAM_TOKEN"))
    admin_chat_id = os.getenv("ADMIN_CHAT_ID")
    if admin_chat_id:
        await bot.send_message(
            chat_id=admin_chat_id,
            text=f"Unanswered question from user {user_id}:\n\n{question}",
        )
