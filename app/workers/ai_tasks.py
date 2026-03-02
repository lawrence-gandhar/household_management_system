# app/workers/ai_tasks.py
"""
Use background tasks for non-blocking recipe generation.

Route posts job → returns 202 Accepted + job_id
Worker processes → stores result in DB
Client polls GET /ai/recipe/{job_id}

This pattern is mandatory at >50k users to prevent HTTP timeout issues
with slow LLM calls (p99 can be 15-30 seconds).
"""
import asyncio
import logging
from uuid import UUID

from celery import Celery

from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "pantrymate",
    broker     = settings.REDIS_URL,
    backend    = settings.REDIS_URL,
    include    = ["app.workers.ai_tasks"],
)
celery_app.conf.update(
    task_serializer       = "json",
    result_serializer     = "json",
    accept_content        = ["json"],
    task_soft_time_limit  = 45,   # graceful shutdown
    task_time_limit       = 60,   # hard kill
    worker_prefetch_multiplier = 1,   # fair dispatch for long tasks
    task_acks_late        = True,     # ack after completion, not on receipt
    task_reject_on_worker_lost = True,
)


@celery_app.task(
    bind=True,
    name="ai.generate_recipe",
    max_retries=2,
    default_retry_delay=5,
)
def generate_recipe_task(
    self,
    user_id: str,
    tier: str,
    preferences: list[str],
    cuisine: str | None,
    max_cook_minutes: int | None,
) -> dict:
    """
    Background task wrapper for recipe generation.
    Runs the full RecipeEngine inside a new event loop.
    """
    return asyncio.get_event_loop().run_until_complete(
        _async_generate(self, user_id, tier, preferences, cuisine, max_cook_minutes)
    )


async def _async_generate(task, user_id, tier, preferences, cuisine, max_cook_mins):
    from app.ai.schemas import RecipeRequest
    from app.db.session import AsyncSessionFactory
    from app.models.enums import SubscriptionTier
    from app.services.cache_service import get_cache_service
    from app.services.openai_service import OpenAIService
    from app.services.recipe_engine import RecipeEngine, RecipeGenerationError

    req = RecipeRequest(
        dietary_preferences      = preferences,
        cuisine_preference       = cuisine,
        max_cook_time_minutes    = max_cook_mins,
    )

    async with AsyncSessionFactory() as db:
        engine = RecipeEngine(
            db                = db,
            cache             = get_cache_service(),
            openai_svc        = OpenAIService(),
            user_id           = UUID(user_id),
            subscription_tier = SubscriptionTier(tier),
        )
        try:
            result = await engine.generate_recipe(req)
            await db.commit()
            return result.model_dump()
        except RecipeGenerationError as exc:
            raise task.retry(exc=exc)