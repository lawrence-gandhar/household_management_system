from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictException, NotFoundException
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate


class CategoryService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def list_categories(
        self,
        *,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Category]:
        stmt = (
            select(Category)
            .order_by(Category.name)
            .offset(skip)
            .limit(limit)
        )
        if active_only:
            stmt = stmt.where(Category.is_active.is_(True))
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def get_category(self, category_id: UUID) -> Category:
        result = await self._db.execute(
            select(Category).where(Category.id == category_id)
        )
        category = result.scalar_one_or_none()
        if category is None:
            raise NotFoundException("Category not found")
        return category

    async def create_category(self, data: CategoryCreate) -> Category:
        category = Category(
            name=data.name,
            description=data.description,
            is_active=data.is_active,
        )
        self._db.add(category)
        try:
            await self._db.flush()
            await self._db.refresh(category)
        except IntegrityError:
            await self._db.rollback()
            raise ConflictException(
                f"A category named '{data.name}' already exists.",
                error_code="CATEGORY_ALREADY_EXISTS",
            )
        return category

    async def update_category(
        self, category_id: UUID, data: CategoryUpdate
    ) -> Category:
        category = await self.get_category(category_id)
        update_data = data.model_dump(exclude_none=True, exclude_unset=True)
        for field, value in update_data.items():
            setattr(category, field, value)
        try:
            await self._db.flush()
            await self._db.refresh(category)
        except IntegrityError:
            await self._db.rollback()
            raise ConflictException(
                f"A category named '{data.name}' already exists.",
                error_code="CATEGORY_ALREADY_EXISTS",
            )
        return category

    async def delete_category(self, category_id: UUID) -> None:
        category = await self.get_category(category_id)
        await self._db.delete(category)
        await self._db.flush()
