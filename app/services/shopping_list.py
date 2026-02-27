from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.shopping_list import ShoppingList, ShoppingListItem
from app.models.user import User
from app.repositories.shopping_list import ShoppingListItemRepository, ShoppingListRepository
from app.schemas.shopping_list import (
    ShoppingListCreate,
    ShoppingListItemCreate,
    ShoppingListItemUpdate,
    ShoppingListUpdate,
)


class ShoppingListService:
    def __init__(self, db: AsyncSession) -> None:
        self._list_repo = ShoppingListRepository(db)
        self._item_repo = ShoppingListItemRepository(db)

    async def list_shopping_lists(self, user: User) -> list[ShoppingList]:
        return await self._list_repo.get_by_user(user.id)

    async def get_shopping_list(self, user: User, list_id: UUID) -> ShoppingList:
        sl = await self._list_repo.get_by_user_and_id(user.id, list_id)
        if not sl:
            raise NotFoundException("Shopping list not found")
        return sl

    async def create_shopping_list(
        self, user: User, data: ShoppingListCreate
    ) -> ShoppingList:
        return await self._list_repo.create_with_items(user.id, data)

    async def update_shopping_list(
        self, user: User, list_id: UUID, data: ShoppingListUpdate
    ) -> ShoppingList:
        sl = await self.get_shopping_list(user, list_id)
        updates = data.model_dump(exclude_none=True, exclude_unset=True)
        return await self._list_repo.update(sl, **updates)

    async def delete_shopping_list(self, user: User, list_id: UUID) -> None:
        sl = await self.get_shopping_list(user, list_id)
        await self._list_repo.delete(sl)

    # ── Items ────────────────────────────────────────────────────────────────

    async def add_item(
        self, user: User, list_id: UUID, data: ShoppingListItemCreate
    ) -> ShoppingListItem:
        await self.get_shopping_list(user, list_id)  # ownership check
        return await self._item_repo.create(
            shopping_list_id=list_id,
            ingredient_name=data.ingredient_name,
            quantity=data.quantity,
            unit=data.unit,
            notes=data.notes,
        )

    async def update_item(
        self,
        user: User,
        list_id: UUID,
        item_id: UUID,
        data: ShoppingListItemUpdate,
    ) -> ShoppingListItem:
        await self.get_shopping_list(user, list_id)  # ownership check
        item = await self._item_repo.get_by_list_and_id(list_id, item_id)
        if not item:
            raise NotFoundException("Shopping list item not found")
        updates = data.model_dump(exclude_none=True, exclude_unset=True)
        return await self._item_repo.update(item, **updates)

    async def delete_item(
        self, user: User, list_id: UUID, item_id: UUID
    ) -> None:
        await self.get_shopping_list(user, list_id)
        item = await self._item_repo.get_by_list_and_id(list_id, item_id)
        if not item:
            raise NotFoundException("Shopping list item not found")
        await self._item_repo.delete(item)

    async def generate_from_recipe(
        self, user: User, recipe_id: UUID
    ) -> ShoppingList:
        """Generate a shopping list from a recipe's ingredients."""
        from app.repositories.recipe import RecipeRepository

        recipe_repo = RecipeRepository(self._list_repo.session)
        recipe = await recipe_repo.get_by_id_with_ingredients(recipe_id)
        if not recipe or recipe.user_id != user.id:
            raise NotFoundException("Recipe not found")

        items = [
            ShoppingListItemCreate(
                ingredient_name=ing.name,
                quantity=float(ing.quantity) if ing.quantity else None,
                unit=ing.unit,
            )
            for ing in recipe.ingredients
        ]
        data = ShoppingListCreate(
            title=f"Ingredients for: {recipe.title}",
            items=items,
        )
        return await self._list_repo.create_with_items(user.id, data)
