from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.shopping_list import ShoppingList, ShoppingListItem
from app.repositories.base import BaseRepository
from app.schemas.shopping_list import ShoppingListCreate


class ShoppingListRepository(BaseRepository[ShoppingList]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ShoppingList, session)

    async def get_by_user(self, user_id: UUID) -> list[ShoppingList]:
        result = await self.session.execute(
            select(ShoppingList)
            .options(selectinload(ShoppingList.items))
            .where(ShoppingList.user_id == user_id)
            .order_by(ShoppingList.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_user_and_id(
        self, user_id: UUID, list_id: UUID
    ) -> ShoppingList | None:
        result = await self.session.execute(
            select(ShoppingList)
            .options(selectinload(ShoppingList.items))
            .where(
                and_(
                    ShoppingList.user_id == user_id,
                    ShoppingList.id == list_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def create_with_items(
        self, user_id: UUID, data: ShoppingListCreate
    ) -> ShoppingList:
        shopping_list = ShoppingList(
            user_id=user_id,
            title=data.title,
        )
        self.session.add(shopping_list)
        await self.session.flush()

        for item_data in data.items:
            item = ShoppingListItem(
                shopping_list_id=shopping_list.id,
                ingredient_name=item_data.ingredient_name,
                quantity=item_data.quantity,
                unit=item_data.unit,
                notes=item_data.notes,
            )
            self.session.add(item)

        await self.session.flush()
        await self.session.refresh(shopping_list)
        return shopping_list


class ShoppingListItemRepository(BaseRepository[ShoppingListItem]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ShoppingListItem, session)

    async def get_by_list_and_id(
        self, list_id: UUID, item_id: UUID
    ) -> ShoppingListItem | None:
        result = await self.session.execute(
            select(ShoppingListItem).where(
                and_(
                    ShoppingListItem.shopping_list_id == list_id,
                    ShoppingListItem.id == item_id,
                )
            )
        )
        return result.scalar_one_or_none()
