import redis.asyncio as aioredis
import json
import os
from typing import Any, Optional

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

_redis: Optional[aioredis.Redis] = None

async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
    return _redis

async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    val = await r.get(key)
    if val:
        return json.loads(val)
    return None

async def cache_set(key: str, value: Any, ttl: int = 3600) -> None:
    r = await get_redis()
    await r.setex(key, ttl, json.dumps(value, default=str))

async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)

async def publish(channel: str, message: dict) -> None:
    r = await get_redis()
    await r.publish(channel, json.dumps(message, default=str))

# TTL constants
TTL_PLAYER_LIST = 43200      # 12 hours — player list rarely changes
TTL_SCHEDULE = 3600          # 1 hour
TTL_DEF_RATINGS = 7200       # 2 hours
TTL_LIVE_SCOREBOARD = 60     # 60 seconds
TTL_SLEEPER_PLAYERS = 86400  # 24 hours
