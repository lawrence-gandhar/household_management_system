"""
Production-ready Pantry Mate unit seeder.

- Idempotent
- PostgreSQL optimized
- Safe to run multiple times
- Australia metric aligned
"""

import asyncio
import logging
import uuid
from decimal import Decimal
from sqlalchemy import text

from app.db.seeders.base import BaseSeeder
from app.db.session import AsyncSessionFactory

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Australian Metric Units
# ─────────────────────────────────────────────────────────────

_DEFAULT_UNITS = [
    # WEIGHT
    ("milligram", "mg", "WEIGHT", "milligram", Decimal("1")),
    ("gram", "g", "WEIGHT", "gram", Decimal("1")),
    ("kilogram", "kg", "WEIGHT", "gram", Decimal("1000")),

    # VOLUME
    ("millilitre", "mL", "VOLUME", "millilitre", Decimal("1")),
    ("litre", "L", "VOLUME", "millilitre", Decimal("1000")),

    # COUNT
    ("piece", "pc", "COUNT", None, None),
    ("pack", "pk", "COUNT", None, None),
    ("box", "bx", "COUNT", None, None),
    ("can", "cn", "COUNT", None, None),
    ("jar", "jr", "COUNT", None, None),
    ("bottle", "bt", "COUNT", None, None),
    ("tub", "tb", "COUNT", None, None),
    ("carton", "ct", "COUNT", None, None),
    ("bunch", "bn", "COUNT", None, None),
    ("dozen", "dz", "COUNT", None, None),
    ("slice", "sl", "COUNT", None, None),
    ("set", "set", "COUNT", None, None),
]


class UnitSeeder(BaseSeeder):

    async def seed(self) -> None:

        stmt = text(
            """
            INSERT INTO units (
                id,
                name,
                short_code,
                type,
                base_unit,
                conversion_factor,
                is_active
            )
            VALUES (
                :id,
                :name,
                :short_code,
                :type,
                :base_unit,
                :conversion_factor,
                TRUE
            )
            ON CONFLICT (name) DO NOTHING
            """
        )

        rows = [
            {
                "id": uuid.uuid4(),
                "name": name,
                "short_code": short_code,
                "type": unit_type,
                "base_unit": base_unit,
                "conversion_factor": conversion_factor,
            }
            for name, short_code, unit_type, base_unit, conversion_factor in _DEFAULT_UNITS
        ]

        result = await self._db.execute(stmt, rows)

        logger.info(
            "UnitSeeder: %d inserted, %d skipped.",
            result.rowcount,
            len(rows) - result.rowcount,
        )


async def run_unit_seeder():
    async with AsyncSessionFactory() as session:
        try:
            await UnitSeeder(session).seed()
            await session.commit()
            logger.info("Unit seeding completed successfully.")
        except Exception:
            await session.rollback()
            logger.exception("UnitSeeder failed — rolled back.")
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_unit_seeder())