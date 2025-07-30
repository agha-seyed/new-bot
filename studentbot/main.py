import os
import logging
import asyncio
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler
)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
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
from studentbot import config

# Load environment variables
load_dotenv()

# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# FastAPI App
app = FastAPI()

# Telegram Application
application = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

@app.get("/")
async def root():
    return {"status": "Bot is running!"}

@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()
        await application.update_queue.put(Update.de_json(data, application.bot))
        logger.info("✅ Webhook received and processed")
        return {"ok": True}
    except Exception as e:
        logger.error(f"❌ Webhook error: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})

async def setup():
    """Setup the bot, database, and webhook."""
    try:
        await create_users_table()
        await create_consultation_requests_table()

        await application.bot.set_webhook(
            url=f"{config.BASE_URL}/webhook",
            secret_token=config.WEBHOOK_SECRET,
        )
        logger.info(f"✅ Webhook set to {config.BASE_URL}/webhook")

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
            get_question_handler(),
        ]:
            for handler in handler_group:
                application.add_handler(handler)

        application.add_handler(
            MessageHandler(
                filters.Regex(r"^(🗑️ Delete Profile|🗑️ حذف پروفایل|🗑️ Elimina profilo)$"),
                delete_profile_handler,
            )
        )

        application.add_handler(
            MessageHandler(
                filters.Regex(r"^(🇬🇧 English|🇮🇷 فارسی|🇮🇹 Italiano)$"),
                language_handler,
            )
        )

        start_scheduler()
        logger.info("✅ Bot setup completed.")
    except Exception as e:
        logger.error(f"❌ Error in setup: {str(e)}")
        raise

@app.on_event("startup")
async def startup_event():
    """Start the Telegram bot and scheduler on FastAPI startup."""
    try:
        logger.info("🚀 Starting Telegram bot...")
        await application.initialize()
        await application.start()
        port = int(os.getenv("PORT", 8080))
        await application.updater.start_webhook(
            listen="0.0.0.0",
            port=port,
            url_path="/webhook",
            webhook_url=f"{config.BASE_URL}/webhook",
            secret_token=config.WEBHOOK_SECRET
        )
        logger.info(f"✅ Bot started successfully, listening on port {port}.")
    except Exception as e:
        logger.error(f"❌ Error starting bot: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Stop the Telegram bot on FastAPI shutdown."""
    try:
        logger.info("🛑 Stopping Telegram bot...")
        await application.updater.stop()
        await application.stop()
        await application.shutdown()
        logger.info("✅ Bot stopped successfully.")
    except Exception as e:
        logger.error(f"❌ Error stopping bot: {str(e)}")

# Entrypoint
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    logger.info(f"🚀 Starting server on port {port}...")
    asyncio.run(setup())
    uvicorn.run("studentbot.main:app", host="0.0.0.0", port=port)
else:
    logger.info("🚀 Scheduling setup task for non-main execution...")
    asyncio.create_task(setup())
