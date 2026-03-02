"""
Production-ready Pantry Mate category seeder.

- Hierarchical (parent → child)
- Idempotent
- PostgreSQL optimized
- Safe to run multiple times
"""

import asyncio
import logging
import uuid
from sqlalchemy import text

from app.db.seeders.base import BaseSeeder
from app.db.session import AsyncSessionFactory

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# Pantry Mate Category Tree (No Alcoholic Category)
# ─────────────────────────────────────────────────────────────

_CATEGORY_TREE = {
    "Pantry": [
        "Grains & Cereals",
        "Pasta & Noodles",
        "Baking Ingredients",
        "Herbs & Spices",
        "Condiments & Sauces",
        "Canned & Preserved Foods",
        "Legumes & Pulses",
        "Snacks",
        "Spreads",
    ],
    "Fresh Produce": [
        "Fruits",
        "Vegetables",
        "Leafy Greens",
        "Root Vegetables",
        "Fresh Herbs",
    ],
    "Proteins": [
        "Meat & Poultry",
        "Seafood",
        "Plant-Based Proteins",
        "Eggs",
    ],
    "Dairy": [
        "Milk",
        "Cheese",
        "Yogurt & Cultured",
        "Butter & Margarine",
        "Milk Alternatives",
    ],
    "Frozen": [
        "Frozen Vegetables",
        "Frozen Fruits",
        "Frozen Meals",
        "Frozen Meat",
        "Frozen Seafood",
    ],
    "Beverages": [
        "Soft Drinks",
        "Juices",
        "Sparkling Water",
        "Tea",
        "Coffee",
        "Energy Drinks",
    ],
    "Bakery": [
        "Bread",
        "Pastries",
        "Wraps & Tortillas",
        "Cakes",
        "Biscuits",
    ],
    "Cooking Essentials": [
        "Oils",
        "Vinegars",
        "Sweeteners",
        "Stocks & Broths",
    ],
    "Kitchen Equipment": [
        "Utensils",
        "Cookware",
        "Knives",
        "Appliances",
        "Storage Containers",
        "Baking Tools",
        "Measuring Tools",
    ],
}


# ─────────────────────────────────────────────────────────────
# Seeder Implementation
# ─────────────────────────────────────────────────────────────

class CategorySeeder(BaseSeeder):
    async def seed(self) -> None:

        # Insert parent categories
        parent_stmt = text(
            """
            INSERT INTO categories (id, name, description, is_active)
            VALUES (:id, :name, :description, TRUE)
            ON CONFLICT (name) DO NOTHING
            """
        )

        parent_rows = [
            {
                "id": uuid.uuid4(),
                "name": parent,
                "description": f"{parent} category",
            }
            for parent in _CATEGORY_TREE.keys()
        ]

        result = await self._db.execute(parent_stmt, parent_rows)
        logger.info("Inserted %d parent categories", result.rowcount)

        # Insert child categories with parent lookup
        child_stmt = text(
            """
            INSERT INTO categories (id, name, description, parent_id, is_active)
            SELECT :id, :name, :description, c.id, TRUE
            FROM categories c
            WHERE c.name = :parent_name
            ON CONFLICT (name) DO NOTHING
            """
        )

        inserted_children = 0

        for parent, children in _CATEGORY_TREE.items():
            for child in children:
                result = await self._db.execute(
                    child_stmt,
                    {
                        "id": uuid.uuid4(),
                        "name": child,
                        "description": f"{child} under {parent}",
                        "parent_name": parent,
                    },
                )
                inserted_children += result.rowcount

        logger.info("Inserted %d child categories", inserted_children)


# ─────────────────────────────────────────────────────────────
# Standalone Runner
# ─────────────────────────────────────────────────────────────

async def run_category_seeder():
    async with AsyncSessionFactory() as session:
        try:
            await CategorySeeder(session).seed()
            await session.commit()
            logger.info("Category seeding completed successfully.")
        except Exception:
            await session.rollback()
            logger.exception("CategorySeeder failed — rolled back.")
            raise


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_category_seeder())