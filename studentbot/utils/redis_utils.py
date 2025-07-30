import logging
from typing import Optional
import redis.asyncio as redis
from studentbot import config

logger = logging.getLogger(__name__)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

class RedisClient:
    """Manages Redis connection and operations for caching."""
    
    def __init__(self):
        self.client: Optional[redis.Redis] = None
        self.namespace = "studentbot:"
        
    async def initialize(self):
        """Initialize Redis connection with connection pool."""
        if not config.REDIS_URL:
            logger.error("❌ REDIS_URL is not set in configuration.")
            return
        
        try:
            self.client = redis.from_url(
                config.REDIS_URL,
                decode_responses=True,
                max_connections=10,
                ssl_cert_reqs=None  # برای Upstash
            )
            # Test connection
            await self.client.ping()
            logger.info("✅ Redis client initialized successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Redis: {str(e)}")
            self.client = None
    
    async def close(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            logger.info("🛑 Redis connection closed.")
    
    async def get_cached_answer(self, question: str) -> Optional[str]:
        """Get a cached answer from Redis."""
        if not self.client:
            logger.warning("⚠️ Redis client is not initialized. Skipping cache check.")
            return None
        
        if not question or not isinstance(question, str):
            logger.warning("⚠️ Invalid question provided for cache lookup.")
            return None
            
        try:
            key = f"{self.namespace}answer:{question}"
            cached = await self.client.get(key)
            if cached:
                logger.info(f"✅ Cache hit for question: {question} (key: {key})")
                return cached
            logger.info(f"🌀 Cache miss for question: {question} (key: {key})")
            return None
        except Exception as e:
            logger.error(f"❌ Error getting cached answer for {question}: {str(e)}")
            return None
    
    async def cache_answer(self, question: str, answer: str, ttl: int = 3600) -> None:
        """Cache an answer in Redis with a TTL (default: 1 hour)."""
        if not self.client:
            logger.warning("⚠️ Redis client is not initialized. Skipping cache set.")
            return
            
        if not question or not answer or not isinstance(question, str) or not isinstance(answer, str):
            logger.warning("⚠️ Invalid question or answer provided for caching.")
            return
            
        try:
            key = f"{self.namespace}answer:{question}"
            await self.client.setex(key, ttl, answer)
            logger.info(f"✅ Cached answer for question: {question} (key: {key}, TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"❌ Error caching answer for {question}: {str(e)}")

# Initialize Redis client
redis_client = RedisClient()
