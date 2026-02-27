from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.enums import RecipeSource
from app.models.recipe import Recipe, RecipeIngredient
from app.repositories.base import BaseRepository
from app.schemas.recipe import RecipeCreate


class RecipeRepository(BaseRepository[Recipe]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Recipe, session)

    async def get_by_user(
        self, user_id: UUID, skip: int = 0, limit: int = 50
    ) -> list[Recipe]:
        result = await self.session.execute(
            select(Recipe)
            .options(selectinload(Recipe.ingredients))
            .where(Recipe.user_id == user_id)
            .order_by(Recipe.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_id_with_ingredients(self, recipe_id: UUID) -> Recipe | None:
        result = await self.session.execute(
            select(Recipe)
            .options(selectinload(Recipe.ingredients))
            .where(Recipe.id == recipe_id)
        )
        return result.scalar_one_or_none()

    async def create_with_ingredients(
        self, user_id: UUID, data: RecipeCreate, is_premium: bool = False
    ) -> Recipe:
        recipe = Recipe(
            user_id=user_id,
            title=data.title,
            description=data.description,
            cuisine_type=data.cuisine_type,
            prep_time_minutes=data.prep_time_minutes,
            cook_time_minutes=data.cook_time_minutes,
            servings=data.servings,
            difficulty=data.difficulty,
            source=data.source,
            source_url=data.source_url,
            instructions=data.instructions,
            tags=data.tags,
            is_premium=is_premium,
        )
        self.session.add(recipe)
        await self.session.flush()

        for ing_data in data.ingredients:
            ingredient = RecipeIngredient(
                recipe_id=recipe.id,
                name=ing_data.name,
                quantity=ing_data.quantity,
                unit=ing_data.unit,
                is_optional=ing_data.is_optional,
                notes=ing_data.notes,
            )
            self.session.add(ingredient)

        await self.session.flush()
        await self.session.refresh(recipe)
        return recipe
