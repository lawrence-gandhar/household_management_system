"""
Production-ready Pantry Mate category-unit seeder.

- Idempotent
- PostgreSQL optimized
- Safe to run multiple times
- Resolves foreign keys via SELECT
"""

import asyncio
import logging
import uuid
from sqlalchemy import text

from app.db.seeders.base import BaseSeeder
from app.db.session import AsyncSessionFactory

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Category → Allowed Units Mapping
# Must match your seeded category names
# ─────────────────────────────────────────────────────────────

_CATEGORY_UNIT_MAP = {
    "Pantry": ["gram", "kilogram", "millilitre", "litre", "pack", "box", "can", "jar"],
    "Fresh Produce": ["piece", "gram", "kilogram", "bunch", "dozen"],
    "Proteins": ["gram", "kilogram", "piece"],
    "Dairy": ["litre", "millilitre", "gram", "kilogram", "tub", "carton"],
    "Frozen": ["gram", "kilogram", "pack"],
    "Beverages": ["millilitre", "litre", "bottle", "can"],
    "Bakery": ["piece", "pack", "slice"],
    "Cooking Essentials": ["millilitre", "litre", "gram", "kilogram", "bottle"],
    "Kitchen Equipment": ["piece", "set"],
}


class CategoryUnitSeeder(BaseSeeder):

    async def seed(self) -> None:

        stmt = text(
            """
            INSERT INTO category_units (
                id,
                category_id,
                unit_id
            )
            SELECT
                :id,
                c.id,
                u.id
            FROM categories c
            JOIN units u ON u.name = :unit_name
            WHERE c.name = :category_name
            ON CONFLICT (category_id, unit_id) DO NOTHING
            """
        )

        inserted = 0

        for category, units in _CATEGORY_UNIT_MAP.items():
            for unit in units:
                result = await self._db.execute(
                    stmt,
                    {
                        "id": uuid.uuid4(),
                        "category_name": category,
                        "unit_name": unit,
                    },
                )
                inserted += result.rowcount

        logger.info("CategoryUnitSeeder: %d mappings inserted.", inserted)


async def run_category_unit_seeder():
    async with AsyncSessionFactory() as session:
        try:
            await CategoryUnitSeeder(session).seed()
            await session.commit()
            logger.info("CategoryUnit seeding completed successfully.")
        except Exception:
            await session.rollback()
            logger.exception("CategoryUnitSeeder failed — rolled back.")
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_category_unit_seeder())