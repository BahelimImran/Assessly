from redis.asyncio import Redis

from app.core.config import REDIS_URL

redis = Redis.from_url(
    REDIS_URL,
    decode_responses=True
)