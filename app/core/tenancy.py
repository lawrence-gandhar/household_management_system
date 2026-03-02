# app/core/tenancy.py
from __future__ import annotations

import hashlib
import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import InventoryItem
from app.models.recipe import Recipe


class UserScopedQuery:
    """
    The ONLY gateway between the AI layer and the database.

    Design contract:
    - Constructed once per request with a locked user_id.
    - Every method hard-filters by self._user_id — there is no
      way to query another user's data through this class.
    - The AI layer receives Python dicts/lists, never ORM objects
      or sessions.  The LLM cannot cause a query to execute.
    """

    def __init__(self, db: AsyncSession, user_id: UUID) -> None:
        self._db      = db
        self._user_id = user_id

    # ── Inventory ─────────────────────────────────────────────────

    async def fetch_inventory_for_ai(self) -> list[dict]:
        """Return minimal, serialisable dicts — never raw ORM objects."""
        stmt = (
            select(InventoryItem)
            .where(InventoryItem.user_id == self._user_id)
            .where(InventoryItem.quantity > 0)
            .order_by(InventoryItem.name)
            .limit(200)          # absolute safety cap
        )
        rows = (await self._db.execute(stmt)).scalars().all()
        return [
            {
                "name":     row.name,
                "quantity": float(row.quantity),
                "unit":     row.quantity_unit or "",
                "category": row.category or "",
            }
            for row in rows
        ]

    # ── Recipe deduplication ──────────────────────────────────────

    async def find_cached_recipe(self, ingredient_hash: str) -> dict | None:
        stmt = (
            select(Recipe)
            .where(Recipe.user_id      == self._user_id)
            .where(Recipe.source       == "ai_generated")
        )
        # If you add ingredient_hash column to Recipe:
        # .where(Recipe.ingredient_hash == ingredient_hash)
        result = await self._db.execute(stmt)
        row = result.scalar_one_or_none()
        return row.recipe_data if row else None   # recipe_data is a JSON column

    async def store_generated_recipe(
        self,
        ingredient_hash: str,
        recipe_data: dict,
        usage_tokens: int,
        cost_usd: float,
    ) -> Recipe:
        recipe = Recipe(
            user_id         = self._user_id,
            title           = recipe_data["title"],
            source          = "ai_generated",
            recipe_data     = recipe_data,  # full JSON stored
        )
        self._db.add(recipe)
        await self._db.flush()
        return recipe


def make_ingredient_hash(ingredients: list[dict]) -> str:
    """Deterministic fingerprint of an ingredient list for cache keying."""
    canonical = sorted(
        [{"n": i["name"].lower().strip(), "q": round(i["quantity"], 1)} for i in ingredients],
        key=lambda x: x["n"],
    )
    return hashlib.sha256(json.dumps(canonical, sort_keys=True).encode()).hexdigest()[:32]