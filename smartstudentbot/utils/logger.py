import sys
from loguru import logger
from smartstudentbot.config import settings

# Configure Loguru
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level=settings.LOG_LEVEL,
    enqueue=True, # Thread safe
    serialize=False # Set to True for JSON logging in production
)

# Optional: Add Sentry if configured (not strictly in requirements but good practice)
if hasattr(settings, "SENTRY_DSN") and settings.SENTRY_DSN:
    import sentry_sdk
    sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=1.0)
