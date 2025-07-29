import os
import redis.asyncio as redis

# Connect to Redis
redis_client = redis.from_url(os.getenv("REDIS_URL"))


async def get_cached_answer(question):
    """Gets a cached answer from Redis."""
    return await redis_client.get(question)


async def cache_answer(question, answer):
    """Caches an answer in Redis."""
    await redis_client.set(question, answer, ex=3600)  # Cache for 1 hour
