import os
import logging
import asyncio

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

from handlers.cmd_start import start
from handlers.language_handler import language_handler
from handlers.profile_handler import profile, delete_profile_handler
from handlers.menu_handler import menu
from handlers.registration_flow import get_registration_handler
from handlers.edit_profile_flow import get_edit_profile_handler
from handlers.isee_handler import get_isee_handler
from handlers.gamification_handler import points, leaderboard
from handlers.news_handler import news
from handlers.consult_handler import get_consultation_handler
from handlers.document_handler import get_document_handler
from handlers.weather_handler import weather
from handlers.cost_handler import get_cost_handler
from handlers.search_handler import get_search_handler
from handlers.ai_handler import get_ai_handler
from handlers.info_handler import get_info_handler
from handlers.arrival_guide_handler import get_arrival_guide_handler
from handlers.admin_handler import get_admin_handler
from handlers.question_handler import get_question_handler
from handlers.feedback_handler import get_feedback_handler
from handlers.migration_handler import get_migration_handler
from handlers.calendar_handler import get_calendar_handler
from utils.db_utils import create_users_table, create_consultation_requests_table
from utils.scheduler import start_scheduler

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI()

# Telegram Application
application = Application.builder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

@app.get("/")
async def root():
    return {"status": "Bot is running!"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        await application.update_queue.put(Update.de_json(data, application.bot))
        return {"ok": True}
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

async def setup():
    create_users_table()
    create_consultation_requests_table()

    await application.bot.set_webhook(
        url=f"{os.getenv('BASE_URL')}/webhook",
        secret_token=os.getenv("WEBHOOK_SECRET"),
    )

    # Register Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("profile", profile))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(get_registration_handler())
    application.add_handler(get_edit_profile_handler())
    application.add_handler(get_isee_handler())
    application.add_handler(CommandHandler("points", points))
    application.add_handler(CommandHandler("leaderboard", leaderboard))
    application.add_handler(CommandHandler("news", news))
    application.add_handler(CommandHandler("weather", weather))

    for handler_group in [
        get_consultation_handler(),
        get_document_handler(),
        get_search_handler(),
        get_ai_handler(),
        get_info_handler(),
        get_arrival_guide_handler(),
        get_admin_handler(),
        get_feedback_handler(),
        get_migration_handler(),
        get_calendar_handler(),
    ]:
        for handler in handler_group:
            application.add_handler(handler)

    application.add_handler(get_question_handler())

    application.add_handler(
        MessageHandler(
            filters.Regex(r"^(🗑️ Delete Profile|🗑️ حذف پروفایل|🗑️ Elimina profilo)$"),
            delete_profile_handler,
        )
    )

    application.add_handler(
        MessageHandler(
            filters.Regex(r"^(🇬🇧 English|🇮🇹 Italiano|🇮🇷 فارسی)$"),
            language_handler,
        )
    )

    start_scheduler()

    logger.info("✅ Bot setup completed.")

# Entrypoint
if __name__ == "__main__":
    asyncio.run(setup())
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
else:
    asyncio.create_task(setup())
