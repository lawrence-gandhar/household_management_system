from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException
from app.models.equipment import Equipment
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserUpdate


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = UserRepository(db)
        self._db = db

    async def get_profile(self, user_id: UUID) -> User:
        user = await self._repo.get_with_equipment(user_id)
        if not user:
            raise NotFoundException("User not found")
        return user

    async def update_profile(self, user: User, data: UserUpdate) -> User:
        updates = data.model_dump(exclude_none=True, exclude_unset=True)
        if not updates:
            return user
        return await self._repo.update(user, **updates)

    async def set_equipment(self, user: User, equipment_ids: list[UUID]) -> User:
        """Replace the user's equipment selection."""
        result = await self._db.execute(
            select(Equipment).where(Equipment.id.in_(equipment_ids))
        )
        equipment_list = list(result.scalars().all())

        # Fully replace the association (SQLAlchemy handles the junction table)
        user.equipment = equipment_list
        await self._db.flush()
        await self._db.refresh(user)
        return user

    async def get_equipment_names(self, user_id: UUID) -> list[str]:
        user = await self._repo.get_with_equipment(user_id)
        if not user:
            return []
        return [eq.name for eq in user.equipment]
