import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from smartstudentbot.config import settings
from smartstudentbot.utils.logger import logger
from smartstudentbot.handlers import (
    cmd_start,
    news_handler,
    isee_handler,
    ai_handler
)

# --- Lifespan Events ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting SmartStudentBot...")

    # Initialize Redis for FSM
    if settings.REDIS_URL:
        redis = Redis.from_url(settings.REDIS_URL)
        storage = RedisStorage(redis=redis)
    else:
        logger.warning("No Redis URL found, falling back to MemoryStorage (NOT for production)")
        storage = MemoryStorage()

    # Initialize Bot and Dispatcher
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)

    # Register Routers
    dp.include_router(cmd_start.router)
    dp.include_router(news_handler.router)
    dp.include_router(isee_handler.router)
    dp.include_router(ai_handler.router) # AI should be last to catch generic text

    # Store in app state
    app.state.bot = bot
    app.state.dp = dp

    # Set Webhook
    try:
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url != settings.webhook_url:
            logger.info(f"Setting webhook to {settings.webhook_url}")
            await bot.set_webhook(
                url=settings.webhook_url,
                secret_token=settings.X_TELEGRAM_BOT_API_SECRET_TOKEN,
                allowed_updates=["message", "callback_query", "my_chat_member"]
            )
    except Exception as e:
        logger.error(f"Failed to set webhook: {e}")

    yield

    # Shutdown
    logger.info("Shutting down...")
    try:
        await bot.delete_webhook()
        await bot.session.close()
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# --- FastAPI App ---
app = FastAPI(title="SmartStudentBot API", lifespan=lifespan)

@app.post(settings.webhook_path)
async def bot_webhook(request: Request):
    """
    Main webhook endpoint for Telegram updates.
    """
    # Verify Secret Token
    secret_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret_token != settings.X_TELEGRAM_BOT_API_SECRET_TOKEN:
        logger.warning("Unauthorized webhook request")
        return {"status": "unauthorized"}

    # Process Update
    bot: Bot = app.state.bot
    dp: Dispatcher = app.state.dp

    try:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot=bot, update=update)
    except Exception as e:
        logger.error(f"Error processing update: {e}")

    return {"status": "ok"}


@app.get("/health")
async def health_check():
    """
    Health check for Render/Uptime robot.
    """
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/ready")
async def readiness_check():
    """
    Deep health check (DB, Redis, etc.)
    """
    # Add actual DB/Redis pings here
    return {"status": "ready"}

if __name__ == "__main__":
    # For local dev only
    import uvicorn
    uvicorn.run("smartstudentbot.main:app", host="0.0.0.0", port=settings.PORT, reload=True)
