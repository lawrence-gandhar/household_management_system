# app/services/recipe_engine.py
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.graph import RECIPE_GRAPH, RecipeState
from app.ai.schemas import GeneratedRecipe, RecipeRequest, RecipeResponse, UsageStats
from app.core.config import settings
from app.core.enums import SubscriptionTier
from app.core.tenancy import UserScopedQuery
from app.models.subscription import Subscription
from app.services.cache_service import CacheService
from app.services.openai_service import OpenAIService

logger = logging.getLogger(__name__)


class RecipeEngine:
    """
    Top-level orchestrator consumed by FastAPI routes and Celery workers.

    This class:
    1. Enforces tier-based rate limits
    2. Constructs scoped dependencies
    3. Runs the LangGraph pipeline
    4. Logs AI usage
    5. Returns a clean, validated response

    Routes and workers never call OpenAI or touch the DB directly.
    """

    def __init__(
        self,
        db: AsyncSession,
        cache: CacheService,
        openai_svc: OpenAIService,
        user_id: UUID,
        subscription_tier: SubscriptionTier,
    ) -> None:
        self._db    = db
        self._cache = cache
        self._ai    = openai_svc
        self._uid   = user_id
        self._tier  = subscription_tier

    async def generate_recipe(self, request: RecipeRequest) -> RecipeResponse:
        # ── 1. Rate limit check ────────────────────────────────────
        limit = (
            settings.AI_LIMIT_FREE_DAILY
            if self._tier == SubscriptionTier.free
            else settings.AI_LIMIT_PREMIUM_DAILY
        )
        allowed, count = await self._cache.check_and_increment_rate(
            self._uid, limit
        )
        if not allowed:
            raise RateLimitExceededError(
                f"Daily AI limit ({limit}) reached. Used: {count}"
            )

        # ── 2. Build scoped query gateway ──────────────────────────
        scoped = UserScopedQuery(self._db, self._uid)

        # ── 3. Run deterministic LangGraph pipeline ────────────────
        initial: RecipeState = {
            "user_id":          str(self._uid),
            "preferences":      request.dietary_preferences,
            "cuisine":          request.cuisine_preference,
            "max_cook_minutes": request.max_cook_time_minutes,
            "ingredients":      [],
            "ingredient_hash":  "",
            "recipe":           None,
            "usage":            None,
            "from_cache":       False,
            "error_code":       None,
            "error_detail":     None,
        }

        final: RecipeState = await RECIPE_GRAPH.ainvoke(
            initial,
            config={
                "configurable": {
                    "scoped_query": scoped,
                    "cache":        self._cache,
                    "openai_svc":   self._ai,
                }
            },
        )

        # ── 4. Handle errors ───────────────────────────────────────
        if final["error_code"]:
            await self._log_usage(final, success=False)
            raise RecipeGenerationError(
                final["error_code"], final.get("error_detail")
            )

        # ── 5. Log usage (non-blocking) ───────────────────────────
        await self._log_usage(final, success=True)

        usage = final.get("usage") or UsageStats(
            model="", prompt_tokens=0, completion_tokens=0,
            total_tokens=0, cost_usd=0.0, latency_ms=0, cache_hit=True,
        )
        usage.cache_hit = final["from_cache"]

        return RecipeResponse(
            recipe    = final["recipe"],
            cache_hit = final["from_cache"],
            cost_usd  = usage.cost_usd,
            tokens    = usage.total_tokens,
        )

    async def _log_usage(self, state: RecipeState, success: bool) -> None:
        from app.models.ai_usage import AIUsageLog
        usage = state.get("usage")
        log   = AIUsageLog(
            user_id           = self._uid,
            model             = usage.model if usage else "unknown",
            prompt_tokens     = usage.prompt_tokens if usage else 0,
            completion_tokens = usage.completion_tokens if usage else 0,
            total_tokens      = usage.total_tokens if usage else 0,
            cost_usd          = usage.cost_usd if usage else 0.0,
            latency_ms        = usage.latency_ms if usage else 0,
            cache_hit         = state["from_cache"],
            success           = success,
            error_code        = state["error_code"],
        )
        self._db.add(log)
        # Intentionally not awaiting flush here — log on commit with main tx


class RateLimitExceededError(Exception):
    pass


class RecipeGenerationError(Exception):
    def __init__(self, code: str, detail: str | None = None):
        self.code   = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")