"""
Recipe importer — parses Schema.org Recipe JSON-LD from a URL,
with a plain-HTML fallback.
"""

import json
import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from app.core.exceptions import BadGatewayException, ValidationException
from app.schemas.recipe import RecipeCreate, RecipeIngredientCreate

logger = logging.getLogger("pantry_mate.recipe_importer")


class RecipeImporter:
    TIMEOUT = 20.0

    async def import_from_url(self, url: str) -> RecipeCreate:
        try:
            async with httpx.AsyncClient(
                timeout=self.TIMEOUT, follow_redirects=True
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise BadGatewayException(
                f"Could not fetch URL (HTTP {exc.response.status_code})"
            )
        except httpx.RequestError as exc:
            raise BadGatewayException(f"Network error fetching URL: {exc}")

        soup = BeautifulSoup(response.text, "lxml")

        recipe = self._try_json_ld(soup) or self._html_fallback(soup, url)
        if not recipe:
            raise ValidationException("Could not extract recipe data from the provided URL")

        return recipe

    # ── JSON-LD (Schema.org) parser ───────────────────────────────────────────

    def _try_json_ld(self, soup: BeautifulSoup) -> Optional[RecipeCreate]:
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                raw = json.loads(script.string or "")
                # May be a single object or a @graph / list
                candidates = raw if isinstance(raw, list) else [raw]
                for obj in candidates:
                    if isinstance(obj, dict) and obj.get("@type") == "Recipe":
                        return self._map_json_ld(obj)
            except (json.JSONDecodeError, AttributeError):
                continue
        return None

    def _map_json_ld(self, data: dict) -> RecipeCreate:
        instructions = self._extract_instructions(data)
        ingredients = self._extract_ingredients(data)

        return RecipeCreate(
            title=data.get("name", "Imported Recipe"),
            description=data.get("description") or "",
            cuisine_type=data.get("recipeCuisine") or "",
            prep_time_minutes=self._parse_iso_duration(data.get("prepTime")),
            cook_time_minutes=self._parse_iso_duration(data.get("cookTime")),
            servings=self._parse_yield(data.get("recipeYield")),
            instructions=instructions,
            source="imported",
            source_url=data.get("url") or "",
            ingredients=ingredients,
        )

    @staticmethod
    def _extract_instructions(data: dict) -> str:
        raw = data.get("recipeInstructions", "")
        if isinstance(raw, str):
            return raw
        if isinstance(raw, list):
            parts = []
            for i, step in enumerate(raw, 1):
                if isinstance(step, dict):
                    parts.append(f"{i}. {step.get('text', str(step))}")
                else:
                    parts.append(f"{i}. {step}")
            return "\n".join(parts)
        return "See source URL for full instructions."

    @staticmethod
    def _extract_ingredients(data: dict) -> list[RecipeIngredientCreate]:
        return [
            RecipeIngredientCreate(name=ing)
            for ing in data.get("recipeIngredient", [])
            if isinstance(ing, str)
        ]

    @staticmethod
    def _parse_iso_duration(value: Optional[str]) -> Optional[int]:
        """Convert ISO 8601 duration (PT30M, PT1H20M) to total minutes."""
        if not value:
            return None
        import re
        hours = int(m.group(1)) if (m := re.search(r"(\d+)H", value)) else 0
        minutes = int(m.group(1)) if (m := re.search(r"(\d+)M", value)) else 0
        total = hours * 60 + minutes
        return total or None

    @staticmethod
    def _parse_yield(value) -> int:
        if not value:
            return 2
        if isinstance(value, list):
            value = value[0]
        import re
        nums = re.findall(r"\d+", str(value))
        return int(nums[0]) if nums else 2

    # ── Plain HTML fallback ───────────────────────────────────────────────────

    def _html_fallback(self, soup: BeautifulSoup, url: str) -> Optional[RecipeCreate]:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else "Imported Recipe"
        return RecipeCreate(
            title=title,
            description=f"Imported from {url}",
            instructions="See source URL for full instructions.",
            source="imported",
            source_url=url,
        )
