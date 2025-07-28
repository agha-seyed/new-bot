import os
import redis

# Connect to Redis
redis_client = redis.from_url(os.getenv("REDIS_URL"))


def get_cached_answer(question):
    """Gets a cached answer from Redis."""
    return redis_client.get(question)


def cache_answer(question, answer):
    """Caches an answer in Redis."""
    redis_client.set(question, answer, ex=3600)  # Cache for 1 hour
