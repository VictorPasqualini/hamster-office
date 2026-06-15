"""Enfileiramento de jobs para os workers (arq sobre Redis)."""

from arq import create_pool
from arq.connections import RedisSettings

from .config import settings

_pool = None


def redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(settings.redis_url)


async def get_pool():
    global _pool
    if _pool is None:
        _pool = await create_pool(redis_settings())
    return _pool


async def enqueue(func: str, *args, **kwargs) -> None:
    pool = await get_pool()
    await pool.enqueue_job(func, *args, **kwargs)
