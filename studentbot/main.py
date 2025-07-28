import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from fastapi import FastAPI, Request
import uvicorn

from studentbot.handlers.cmd_start import start
from studentbot.handlers.language_handler import language_handler
from studentbot.handlers.profile_handler import profile, delete_profile_handler
from studentbot.handlers.menu_handler import menu
from studentbot.handlers.registration_flow import get_registration_handler
from studentbot.handlers.edit_profile_flow import get_edit_profile_handler
from studentbot.handlers.isee_handler import get_isee_handler
from studentbot.handlers.gamification_handler import points, leaderboard
from studentbot.handlers.news_handler import news
from studentbot.handlers.consult_handler import get_consultation_handler
from studentbot.handlers.document_handler import get_document_handler
from studentbot.handlers.weather_handler import weather
from studentbot.handlers.cost_handler import get_cost_handler
from studentbot.handlers.search_handler import get_search_handler
from studentbot.handlers.ai_handler import get_ai_handler
from studentbot.handlers.info_handler import get_info_handler
from studentbot.handlers.arrival_guide_handler import get_arrival_guide_handler
from studentbot.handlers.admin_handler import get_admin_handler
from studentbot.handlers.question_handler import get_question_handler
from studentbot.handlers.feedback_handler import get_feedback_handler
from studentbot.handlers.migration_handler import get_migration_handler
from studentbot.handlers.calendar_handler import get_calendar_handler
from studentbot.utils.db_utils import create_users_table, create_consultation_requests_table
from studentbot.utils.scheduler import start_scheduler

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

app = FastAPI()
application = Application.builder().token(os.getenv("TELEGRAM_TOKEN")).build()

@app.post("/webhook")
async def webhook(request: Request):
    """Handle webhook updates from Telegram."""
    await application.update_queue.put(
        Update.de_json(await request.json(), application.bot)
    )
    return {"ok": True}

async def main() -> None:
    """Start the bot."""
    # Create the users table if it doesn't already exist
    create_users_table()
    create_consultation_requests_table()

    # Set webhook
    await application.bot.set_webhook(
        url=f"{os.getenv('BASE_URL')}/webhook",
        secret_token=os.getenv("WEBHOOK_SECRET"),
    )

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(get_registration_handler())
    application.add_handler(get_edit_profile_handler())
    application.add_handler(get_isee_handler())
    application.add_handler(CommandHandler("points", points))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("news", news))
    for handler in get_consultation_handler():
        application.add_handler(handler)
    for handler in get_document_handler():
        application.add_handler(handler)
    application.add_handler(CommandHandler("weather", weather))
    application.add_handler(get_cost_handler())
    for handler in get_search_handler():
        application.add_handler(handler)
    for handler in get_ai_handler():
        application.add_handler(handler)
    for handler in get_info_handler():
        application.add_handler(handler)
    for handler in get_arrival_guide_handler():
        application.add_handler(handler)
    for handler in get_admin_handler():
        application.add_handler(handler)
    application.add_handler(get_question_handler())
    for handler in get_feedback_handler():
        application.add_handler(handler)
    for handler in get_migration_handler():
        application.add_handler(handler)
    for handler in get_calendar_handler():
        application.add_handler(handler)
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^(🗑️ Delete Profile|🗑️ حذف پروفایل|🗑️ Elimina profilo)$"),
            delete_profile_handler,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^(🇬🇧 English|🇮🇹 Italiano|🇮🇷 فارسی)$"), language_handler
        )
    )

    # Run the bot until the user presses Ctrl-C
    start_scheduler()
    application.run_polling()


if __name__ == "__main__":
    main()
else:
    import asyncio

    application.bot_data["dp"] = application
    application.bot_data["app"] = app

    loop = asyncio.get_event_loop()
    if loop.is_running():
        loop.create_task(main())
    else:
        loop.run_until_complete(main())
