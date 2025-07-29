import os
import logging
import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Connect to Redis
try:
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise ValueError("REDIS_URL environment variable is not set.")
    redis_client = redis.from_url(redis_url)
    logger.info("✅ Redis client initialized successfully.")
except Exception as e:
    logger.error(f"❌ Failed to connect to Redis: {e}")
    redis_client = None


async def get_cached_answer(question: str) -> str | None:
    """Gets a cached answer from Redis."""
    if not redis_client:
        logger.warning("⚠️ Redis client is not initialized. Skipping cache check.")
        return None
    try:
        cached = await redis_client.get(question)
        if cached:
            logger.info(f"✅ Cache hit for question: {question}")
        else:
            logger.info(f"🌀 Cache miss for question: {question}")
        return cached.decode() if cached else None
    except Exception as e:
        logger.error(f"❌ Error getting cached answer: {e}")
        return None


async def cache_answer(question: str, answer: str, ttl: int = 3600) -> None:
    """Caches an answer in Redis for a given time (default: 1 hour)."""
    if not redis_client:
        logger.warning("⚠️ Redis client is not initialized. Skipping cache set.")
        return
    try:
        await redis_client.set(question, answer, ex=ttl)
        logger.info(f"✅ Cached answer for question: {question}")
    except Exception as e:
        logger.error(f"❌ Error caching answer: {e}")
