"""Cliente Redis compartilhado (pub/sub do realtime, filas)."""

from redis.asyncio import Redis

from .config import settings

_redis: Redis | None = None


def get_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = Redis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def publish(channel: str, message: str) -> None:
    await get_redis().publish(channel, message)
