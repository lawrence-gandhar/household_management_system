"""Production-ready category seeder.

Seeds the ``categories`` table with a default catalog.  Safe to run
multiple times — existing rows (matched by ``name``) are left unchanged.

CLI usage
---------
Run from the project root::

    python -m app.db.seeders.category_seeder

Startup integration (optional)
--------------------------------
Call :func:`run_category_seeder` from your FastAPI lifespan after the DB is
ready.  It opens its own short-lived session and commits on success::

    from app.db.seeders.category_seeder import run_category_seeder

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await run_category_seeder()
        yield
"""

import asyncio
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.seeders.base import BaseSeeder
from app.db.session import AsyncSessionFactory

logger = logging.getLogger(__name__)

# ── Default category catalog ───────────────────────────────────────────────────

_DEFAULT_CATEGORIES: list[dict] = [
    {
        "name": "Utensils",
        "description": (
            "Everyday hand tools used during meal preparation and serving, "
            "such as spatulas, ladles, whisks, and tongs."
        ),
    },
    {
        "name": "Kitchenware",
        "description": (
            "General kitchen accessories and storage items including bowls, "
            "colanders, cutting boards, and measuring tools."
        ),
    },
    {
        "name": "Cookware",
        "description": (
            "Pots, pans, and other vessels used directly on a heat source "
            "for boiling, frying, sautéing, and simmering."
        ),
    },
    {
        "name": "Knives",
        "description": (
            "Chef's knives, paring knives, bread knives, and other bladed "
            "tools used for chopping, slicing, and dicing."
        ),
    },
    {
        "name": "Grocery",
        "description": (
            "Pantry staples and packaged goods such as pasta, canned goods, "
            "oils, condiments, and baking supplies."
        ),
    },
    {
        "name": "Fruits",
        "description": (
            "Fresh, frozen, and dried fruits used in cooking, baking, "
            "smoothies, and as standalone snacks."
        ),
    },
    {
        "name": "Meat and Poultry",
        "description": (
            "Fresh and frozen cuts of beef, pork, lamb, chicken, turkey, "
            "and other animal proteins."
        ),
    },
]


# ── Seeder class ───────────────────────────────────────────────────────────────


class CategorySeeder(BaseSeeder):
    """Inserts default categories using a single bulk statement.

    Uses ``INSERT … ON CONFLICT (name) DO NOTHING`` so running the seeder
    again after adding new categories only inserts the missing rows and
    leaves existing ones untouched.
    """

    async def seed(self) -> None:
        rows = [
            {
                "id": uuid.uuid4(),
                "name": cat["name"],
                "description": cat["description"],
                "is_active": True,
            }
            for cat in _DEFAULT_CATEGORIES
        ]

        # Raw SQL gives us access to ON CONFLICT DO NOTHING which is not
        # available through the ORM insert() without extra gymnastics.
        stmt = text(
            """
            INSERT INTO categories (id, name, description, is_active)
            VALUES (:id, :name, :description, :is_active)
            ON CONFLICT (name) DO NOTHING
            """
        )

        result = await self._db.execute(stmt, rows)
        inserted = result.rowcount
        skipped = len(rows) - inserted

        logger.info(
            "CategorySeeder: %d inserted, %d already existed (skipped).",
            inserted,
            skipped,
        )


# ── Standalone helper ──────────────────────────────────────────────────────────


async def run_category_seeder() -> None:
    """Open a fresh session, run the seeder, and commit.

    Safe to call from the FastAPI lifespan or any async entry-point.
    Rolls back automatically on error.
    """
    async with AsyncSessionFactory() as session:
        try:
            await CategorySeeder(session).seed()
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("CategorySeeder failed — transaction rolled back.")
            raise


# ── CLI entry-point ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
    )
    asyncio.run(run_category_seeder())
    logger.info("Done.")
