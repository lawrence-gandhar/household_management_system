# app/services/cache_service.py
from __future__ import annotations

import json
import logging
from uuid import UUID

import redis.asyncio as aioredis

from app.ai.schemas import GeneratedRecipe
from app.core.config import settings

logger = logging.getLogger(__name__)

_RECIPE_PREFIX = "pm:recipe:"
_RATE_PREFIX   = "pm:rate:"


class CacheService:
    """
    Redis-backed cache service.

    Key schema:
      pm:recipe:{user_id}:{ingredient_hash}   → JSON recipe, TTL=1h
      pm:rate:{user_id}:daily                 → integer counter, TTL=24h
    """

    def __init__(self, client: aioredis.Redis) -> None:
        self._r = client

    # ── Recipe cache ──────────────────────────────────────────────

    def _recipe_key(self, user_id: str | UUID, h: str) -> str:
        return f"{_RECIPE_PREFIX}{user_id}:{h}"

    async def get_recipe(self, user_id: str | UUID, h: str) -> GeneratedRecipe | None:
        raw = await self._r.get(self._recipe_key(user_id, h))
        if raw is None:
            return None
        try:
            return GeneratedRecipe.model_validate_json(raw)
        except Exception:
            logger.warning("Corrupt cache entry for user=%s hash=%s", user_id, h[:8])
            return None

    async def set_recipe(
        self,
        user_id: str | UUID,
        h: str,
        recipe: GeneratedRecipe,
        ttl: int | None = None,
    ) -> None:
        await self._r.setex(
            self._recipe_key(user_id, h),
            ttl or settings.REDIS_AI_CACHE_TTL_S,
            recipe.model_dump_json(),
        )

    # ── Rate limiting ──────────────────────────────────────────────

    def _rate_key(self, user_id: str | UUID) -> str:
        return f"{_RATE_PREFIX}{user_id}:daily"

    async def check_and_increment_rate(
        self, user_id: str | UUID, limit: int
    ) -> tuple[bool, int]:
        """
        Atomic check-and-increment.
        Returns (allowed: bool, current_count: int).
        """
        key   = self._rate_key(user_id)
        pipe  = self._r.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        count, ttl = await pipe.execute()

        if ttl < 0:   # key just created, set expiry
            await self._r.expire(key, settings.REDIS_RATE_WINDOW_S)

        return count <= limit, count

    async def get_daily_count(self, user_id: str | UUID) -> int:
        raw = await self._r.get(self._rate_key(user_id))
        return int(raw) if raw else 0


# ── Dependency ────────────────────────────────────────────────────

_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _pool


def get_cache_service() -> CacheService:
    return CacheService(get_redis())