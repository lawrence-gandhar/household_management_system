"""
AI Scanner integration interface.

The `BaseAIScanner` abstract class defines the contract.
`MockAIScanner` is the placeholder for development / testing.

To use a real AI service, subclass `BaseAIScanner`, implement all methods,
and update `get_ai_scanner()` to return your implementation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional

from app.core.enums import QuantityLevel


@dataclass
class ScanResult:
    name: str
    is_packaged: bool
    quantity_level: str = QuantityLevel.full
    barcode: Optional[str] = None
    brand: Optional[str] = None
    confidence: float = 1.0


@dataclass
class RecipeData:
    title: str
    description: str
    cuisine_type: str
    prep_time_minutes: int
    cook_time_minutes: int
    servings: int
    difficulty: str
    instructions: str
    ingredients: list[dict] = field(default_factory=list)


class BaseAIScanner(ABC):
    @abstractmethod
    async def scan_packaged(self, image_bytes: bytes) -> ScanResult: ...

    @abstractmethod
    async def scan_fresh(self, image_bytes: bytes) -> ScanResult: ...

    @abstractmethod
    async def generate_recipes(
        self,
        ingredients: list[str],
        equipment: list[str],
        cuisine: Optional[str],
        time_constraint: Optional[int],
        count: int,
    ) -> list[RecipeData]: ...


class MockAIScanner(BaseAIScanner):
    """
    Deterministic placeholder — returns sensible dummy data so the rest of
    the stack can be exercised without a real AI service configured.
    """

    async def scan_packaged(self, image_bytes: bytes) -> ScanResult:
        return ScanResult(
            name="Canned Tomatoes",
            is_packaged=True,
            quantity_level=QuantityLevel.full,
            barcode="5000000012345",
            brand="Generic Brand",
            confidence=0.95,
        )

    async def scan_fresh(self, image_bytes: bytes) -> ScanResult:
        return ScanResult(
            name="Fresh Tomato",
            is_packaged=False,
            quantity_level=QuantityLevel.full,
            confidence=0.88,
        )

    async def generate_recipes(
        self,
        ingredients: list[str],
        equipment: list[str],
        cuisine: Optional[str],
        time_constraint: Optional[int],
        count: int,
    ) -> list[RecipeData]:
        top_ingredients = ingredients[:5]
        cuisine_label = cuisine or "International"
        time_label = f"{time_constraint} min" if time_constraint else "~30 min"

        return [
            RecipeData(
                title=f"{cuisine_label} Bowl #{i + 1}",
                description=(
                    f"A quick {cuisine_label.lower()} dish using "
                    f"{', '.join(top_ingredients[:3])}. Ready in {time_label}."
                ),
                cuisine_type=cuisine_label,
                prep_time_minutes=10,
                cook_time_minutes=time_constraint or 20,
                servings=2,
                difficulty="easy",
                instructions=(
                    "1. Prepare and wash all ingredients.\n"
                    "2. Heat oil in a pan over medium heat.\n"
                    "3. Add ingredients and cook for 15-20 minutes.\n"
                    "4. Season to taste and serve hot."
                ),
                ingredients=[
                    {"name": ing, "quantity": 1.0, "unit": "piece"}
                    for ing in top_ingredients
                ],
            )
            for i in range(count)
        ]


def get_ai_scanner() -> BaseAIScanner:
    """
    Factory function. Swap `MockAIScanner` for a real implementation
    by reading from settings (e.g. settings.AI_SERVICE_URL).
    """
    return MockAIScanner()
