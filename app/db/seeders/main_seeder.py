"""
Master seeder runner.

Executes all seeders in correct dependency order.
Safe to run on every startup (idempotent).
"""

import logging

from app.db.session import AsyncSessionFactory
from app.db.seeders.units_seeder import UnitSeeder
from app.db.seeders.category_seeder import CategorySeeder
from app.db.seeders.category_units_seeders import CategoryUnitSeeder

logger = logging.getLogger(__name__)


async def run_all_seeders() -> None:
    async with AsyncSessionFactory() as session:
        try:
            logger.info("Running UnitSeeder...")
            await UnitSeeder(session).seed()

            logger.info("Running CategorySeeder...")
            await CategorySeeder(session).seed()

            logger.info("Running CategoryUnitSeeder...")
            await CategoryUnitSeeder(session).seed()

            await session.commit()
            logger.info("All seeders completed successfully.")

        except Exception:
            await session.rollback()
            logger.exception("Seeder execution failed — rolled back.")
            raise