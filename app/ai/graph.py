# app/ai/graph.py
from __future__ import annotations

import logging
from typing import TypedDict, Any

from langgraph.graph import END, StateGraph

from app.ai.prompts import (
    RECIPE_SYSTEM_PROMPT,
    PromptTooLargeError,
    build_recipe_prompt,
)
from app.ai.schemas import GeneratedRecipe, UsageStats
from app.core.tenancy import UserScopedQuery, make_ingredient_hash
from app.services.cache_service import CacheService
from app.services.openai_service import (
    OpenAIService,
    OpenAIUnavailableError,
    OutputValidationError,
)
from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Graph state ───────────────────────────────────────────────────────────────

class RecipeState(TypedDict):
    # Inputs (set by caller before graph runs)
    user_id:            str
    preferences:        list[str]
    cuisine:            str | None
    max_cook_minutes:   int | None

    # Populated by nodes
    ingredients:        list[dict]
    ingredient_hash:    str
    recipe:             GeneratedRecipe | None
    usage:              UsageStats | None
    from_cache:         bool

    # Error control
    error_code:         str | None   # None = success
    error_detail:       str | None


# ── Nodes ─────────────────────────────────────────────────────────────────────

async def node_fetch_inventory(
    state: RecipeState,
    *,
    scoped_query: UserScopedQuery,
) -> RecipeState:
    """
    Pull user's inventory through the UserScopedQuery gate.
    The LLM has no visibility into this step.
    """
    ingredients = await scoped_query.fetch_inventory_for_ai()

    if not ingredients:
        return {**state, "error_code": "no_ingredients", "ingredients": []}

    return {
        **state,
        "ingredients":      ingredients,
        "ingredient_hash":  make_ingredient_hash(ingredients),
        "error_code":       None,
    }


async def node_check_cache(
    state: RecipeState,
    *,
    cache: CacheService,
    scoped_query: UserScopedQuery,
) -> RecipeState:
    """Check Redis hot cache then DB warm cache before calling the LLM."""
    if state["error_code"]:
        return state

    h = state["ingredient_hash"]

    # 1. Redis (sub-millisecond)
    cached = await cache.get_recipe(state["user_id"], h)
    if cached:
        logger.info("Cache HIT (Redis) user=%s hash=%s", state["user_id"], h[:8])
        return {**state, "recipe": cached, "from_cache": True}

    # 2. Database (warm path — avoids re-calling OpenAI for same ingredients)
    db_recipe = await scoped_query.find_cached_recipe(h)
    if db_recipe:
        parsed = GeneratedRecipe.model_validate(db_recipe)
        await cache.set_recipe(state["user_id"], h, parsed)   # backfill Redis
        logger.info("Cache HIT (DB) user=%s hash=%s", state["user_id"], h[:8])
        return {**state, "recipe": parsed, "from_cache": True}

    return {**state, "from_cache": False}


async def node_generate(
    state: RecipeState,
    *,
    openai_svc: OpenAIService,
) -> RecipeState:
    if state["error_code"] or state.get("from_cache"):
        return state

    try:
        user_prompt = build_recipe_prompt(
            ingredients      = state["ingredients"],
            preferences      = state["preferences"],
            cuisine          = state["cuisine"],
            max_cook_minutes = state["max_cook_minutes"],
        )
    except PromptTooLargeError:
        return {**state, "error_code": "prompt_too_large"}

    try:
        recipe, usage = await openai_svc.structured_completion(
            model         = settings.OPENAI_MODEL_RECIPE,
            system_prompt = RECIPE_SYSTEM_PROMPT,
            user_prompt   = user_prompt,
            schema        = GeneratedRecipe,
            temperature   = 0.3,
        )
        return {**state, "recipe": recipe, "usage": usage}

    except OpenAIUnavailableError:
        return {**state, "error_code": "service_unavailable"}
    except OutputValidationError as e:
        logger.warning("LLM output failed validation user=%s: %s", state["user_id"], e)
        return {**state, "error_code": "invalid_output", "error_detail": str(e)}


async def node_validate_output(state: RecipeState) -> RecipeState:
    """
    Defence-in-depth: verify the recipe only uses ingredients
    that were actually in the user's inventory.
    Catches prompt injection that makes the LLM hallucinate extra ingredients.
    """
    if state["error_code"] or state.get("from_cache"):
        return state

    recipe      = state["recipe"]
    inv_names   = {i["name"].lower() for i in state["ingredients"]}

    for used in recipe.ingredients_used:
        used_lower = used.lower()
        # Allow if any inventory item name is a substring match
        if not any(inv in used_lower or used_lower in inv for inv in inv_names):
            logger.warning(
                "Recipe injected non-inventory ingredient '%s' user=%s",
                used, state["user_id"],
            )
            return {**state, "error_code": "injection_detected", "recipe": None}

    return state


async def node_persist(
    state: RecipeState,
    *,
    scoped_query: UserScopedQuery,
    cache: CacheService,
) -> RecipeState:
    """Store new recipe to DB and warm up Redis."""
    if state["error_code"] or state.get("from_cache") or not state.get("recipe"):
        return state

    usage = state.get("usage")
    await scoped_query.store_generated_recipe(
        ingredient_hash = state["ingredient_hash"],
        recipe_data     = state["recipe"].model_dump(),
        usage_tokens    = usage.total_tokens if usage else 0,
        cost_usd        = usage.cost_usd if usage else 0.0,
    )
    await cache.set_recipe(state["user_id"], state["ingredient_hash"], state["recipe"])
    return state


# ── Routing ───────────────────────────────────────────────────────────────────

def _route_after_cache(state: RecipeState) -> str:
    if state["error_code"]:  return "end"
    if state["from_cache"]:  return "end"
    return "generate"


def _route_after_validate(state: RecipeState) -> str:
    if state["error_code"]:  return "end"
    return "persist"


# ── Graph construction ────────────────────────────────────────────────────────

def build_recipe_graph() -> Any:
    """
    Deterministic graph — no free-form agent loops.
    Every node has a defined role; control flow is explicit.
    """
    g = StateGraph(RecipeState)

    g.add_node("fetch",    node_fetch_inventory)
    g.add_node("cache",    node_check_cache)
    g.add_node("generate", node_generate)
    g.add_node("validate", node_validate_output)
    g.add_node("persist",  node_persist)

    g.set_entry_point("fetch")
    g.add_edge("fetch", "cache")

    g.add_conditional_edges(
        "cache",
        _route_after_cache,
        {"generate": "generate", "end": END},
    )
    g.add_edge("generate", "validate")
    g.add_conditional_edges(
        "validate",
        _route_after_validate,
        {"persist": "persist", "end": END},
    )
    g.add_edge("persist", END)

    return g.compile()


RECIPE_GRAPH = build_recipe_graph()