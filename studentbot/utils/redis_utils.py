import logging
from typing import Optional
import redis.asyncio as redis
from studentbot import config

logger = logging.getLogger(__name__)

class RedisClient:
    """Manages Redis connection and caching operations."""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.namespace = "studentbot:"
    
    async def initialize(self):
        """Initialize Redis connection with connection pool."""
        if not config.REDIS_URL:
            logger.error("❌ REDIS_URL is not set")
            raise ValueError("Missing REDIS_URL")
        
        try:
            self.client = redis.from_url(
                config.REDIS_URL,
                decode_responses=True,
                max_connections=10,
                ssl_cert_reqs=None
            )
            await self.client.ping()
            logger.info("✅ Redis client initialized")
        except redis.RedisError as e:
            logger.error(f"❌ Failed to initialize Redis: {str(e)}")
            raise
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("🛑 Redis connection closed")
            self.client = None
    
    async def get_cached_answer(self, question: str) -> Optional[str]:
        """Get a cached answer from Redis."""
        if not self.client:
            logger.warning("⚠️ Redis client is not initialized")
            return None
        
        if not question or not isinstance(question, str):
            logger.warning("⚠️ Invalid question provided")
            return None
        
        try:
            key = f"{self.namespace}answer:{question}"
            cached = await self.client.get(key)
            logger.info(f"{'✅ Cache hit' if cached else '🌀 Cache miss'} for question: {question}")
            return cached
        except redis.RedisError as e:
            logger.error(f"❌ Error getting cached answer: {str(e)}")
            return None
    
    async def cache_answer(self, question: str, answer: str, ttl: int = 3600) -> None:
        """Cache an answer in Redis with a TTL (default: 1 hour)."""
        if not self.client:
            logger.warning("⚠️ Redis client is not initialized")
            return
        
        if not question or not answer or not isinstance(question, str) or not isinstance(answer, str):
            logger.warning("⚠️ Invalid question or answer provided")
            return
        
        try:
            key = f"{self.namespace}answer:{question}"
            await self.client.setex(key, ttl, answer)
            logger.info(f"✅ Cached answer for question: {question} (TTL: {ttl}s)")
        except redis.RedisError as e:
            logger.error(f"❌ Error caching answer: {str(e)}")

redis_client = RedisClient()
