from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import SubscriptionTier
from app.core.exceptions import NotFoundException, ValidationException
from app.integrations.ai_scanner import get_ai_scanner
from app.integrations.recipe_importer import RecipeImporter
from app.models.recipe import Recipe
from app.models.user import User
from app.repositories.inventory import InventoryRepository
from app.repositories.recipe import RecipeRepository
from app.schemas.recipe import RecipeCreate, RecipeGenerateRequest, RecipeImportRequest, RecipeOut
from app.services.user import UserService


class RecipeService:
    def __init__(self, db: AsyncSession) -> None:
        self._recipe_repo = RecipeRepository(db)
        self._inventory_repo = InventoryRepository(db)
        self._user_service = UserService(db)

    async def list_recipes(
        self, user: User, skip: int = 0, limit: int = 50
    ) -> list[Recipe]:
        return await self._recipe_repo.get_by_user(user.id, skip=skip, limit=limit)

    async def get_recipe(self, user: User, recipe_id: UUID) -> Recipe:
        recipe = await self._recipe_repo.get_by_id_with_ingredients(recipe_id)
        if not recipe or recipe.user_id != user.id:
            raise NotFoundException("Recipe not found")
        return recipe

    async def generate_from_inventory(
        self, user: User, payload: RecipeGenerateRequest
    ) -> list[Recipe]:
        ingredient_names = await self._inventory_repo.get_item_names_for_user(user.id)
        if not ingredient_names:
            raise ValidationException(
                "Your inventory is empty. Add items before generating recipes."
            )

        equipment_names = await self._user_service.get_equipment_names(user.id)

        # Enforce free tier: max 1 recipe
        sub = user.subscription
        is_premium = sub is not None and sub.tier == SubscriptionTier.premium
        max_recipes = payload.count if is_premium else settings.FREE_RECIPE_LIMIT

        scanner = get_ai_scanner()
        recipes_data = await scanner.generate_recipes(
            ingredients=ingredient_names,
            equipment=equipment_names,
            cuisine=payload.cuisine_preference,
            time_constraint=payload.time_constraint_minutes,
            count=max_recipes,
        )

        saved: list[Recipe] = []
        for rd in recipes_data[:max_recipes]:
            recipe_create = RecipeCreate(
                title=rd.title,
                description=rd.description,
                cuisine_type=rd.cuisine_type,
                prep_time_minutes=rd.prep_time_minutes,
                cook_time_minutes=rd.cook_time_minutes,
                servings=rd.servings,
                difficulty=rd.difficulty,
                source="generated",
                instructions=rd.instructions,
                ingredients=[
                    {"name": i["name"], "quantity": i.get("quantity"), "unit": i.get("unit")}
                    for i in rd.ingredients
                ],
            )
            recipe = await self._recipe_repo.create_with_ingredients(
                user.id, recipe_create, is_premium=False
            )
            saved.append(recipe)

        return saved

    async def import_from_url(
        self, user: User, payload: RecipeImportRequest
    ) -> Recipe:
        """Premium-only: parse and persist a recipe from an external URL."""
        importer = RecipeImporter()
        recipe_create = await importer.import_from_url(str(payload.url))

        return await self._recipe_repo.create_with_ingredients(
            user.id, recipe_create, is_premium=True
        )

    async def delete_recipe(self, user: User, recipe_id: UUID) -> None:
        recipe = await self.get_recipe(user, recipe_id)
        await self._recipe_repo.delete(recipe)
