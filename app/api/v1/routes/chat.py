# app/api/v1/routes/chat.py
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.schemas import RecipeRequest, RecipeResponse
from app.api.v1.dependencies import get_current_user
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User
from app.services.cache_service import CacheService, get_cache_service
from app.services.openai_service import OpenAIService
from app.services.recipe_engine import (
    RateLimitExceededError,
    RecipeEngine,
    RecipeGenerationError,
)

router = APIRouter(prefix="/ai", tags=["AI"])

# Singleton — one HTTP client pool for the app lifetime
_openai_svc = OpenAIService()


@router.post(
    "/recipe",
    response_model=RecipeResponse,
    summary="Generate a recipe from available inventory",
)
async def generate_recipe(
    body:    RecipeRequest,
    db:      AsyncSession   = Depends(get_db),
    cache:   CacheService   = Depends(get_cache_service),
    user:    User           = Depends(get_current_user),
) -> RecipeResponse:
    """
    Generate a recipe using only the authenticated user's pantry inventory.

    - Results are cached per inventory state (Redis + DB).
    - Rate-limited by subscription tier.
    - LLM output is fully validated before return.
    """
    # Resolve tier from subscription
    tier = user.subscription.tier if user.subscription else "free"

    engine = RecipeEngine(
        db               = db,
        cache            = cache,
        openai_svc       = _openai_svc,
        user_id          = user.id,
        subscription_tier= tier,
    )

    try:
        return await engine.generate_recipe(body)

    except RateLimitExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc))

    except RecipeGenerationError as exc:
        status_map = {
            "no_ingredients":    (400, "No ingredients in pantry"),
            "service_unavailable":(503, "AI service temporarily unavailable"),
            "invalid_output":    (502, "AI returned an invalid response"),
            "injection_detected":(422, "Recipe validation failed"),
            "timeout":           (504, "AI request timed out"),
        }
        http_status, msg = status_map.get(exc.code, (500, "Unexpected error"))
        raise HTTPException(status_code=http_status, detail=msg)