from datetime import date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.inventory import ExpiryTracking, InventoryItem
from app.repositories.base import BaseRepository


class InventoryRepository(BaseRepository[InventoryItem]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(InventoryItem, session)

    async def get_by_user(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[InventoryItem]:
        result = await self.session.execute(
            select(InventoryItem)
            .options(selectinload(InventoryItem.expiry))
            .where(InventoryItem.user_id == user_id)
            .order_by(InventoryItem.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_user_and_id(
        self, user_id: UUID, item_id: UUID
    ) -> InventoryItem | None:
        result = await self.session.execute(
            select(InventoryItem)
            .options(selectinload(InventoryItem.expiry))
            .where(
                and_(
                    InventoryItem.user_id == user_id,
                    InventoryItem.id == item_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def count_by_user(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(InventoryItem).where(
                InventoryItem.user_id == user_id
            )
        )
        return result.scalar_one()

    async def get_item_names_for_user(self, user_id: UUID) -> list[str]:
        result = await self.session.execute(
            select(InventoryItem.name).where(InventoryItem.user_id == user_id)
        )
        return list(result.scalars().all())


class ExpiryRepository(BaseRepository[ExpiryTracking]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ExpiryTracking, session)

    async def get_upcoming(
        self, user_id: UUID, days_ahead: int = 3
    ) -> list[ExpiryTracking]:
        cutoff = date.today() + timedelta(days=days_ahead)
        result = await self.session.execute(
            select(ExpiryTracking)
            .options(selectinload(ExpiryTracking.inventory_item))
            .where(
                and_(
                    ExpiryTracking.user_id == user_id,
                    ExpiryTracking.expiry_date <= cutoff,
                    ExpiryTracking.expiry_date >= date.today(),
                )
            )
            .order_by(ExpiryTracking.expiry_date)
        )
        return list(result.scalars().all())

    async def get_pending_notifications(self) -> list[ExpiryTracking]:
        """Fetch all expiry records due tomorrow that haven't been notified yet."""
        tomorrow = date.today() + timedelta(days=1)
        result = await self.session.execute(
            select(ExpiryTracking)
            .options(selectinload(ExpiryTracking.inventory_item))
            .where(
                and_(
                    ExpiryTracking.expiry_date == tomorrow,
                    ExpiryTracking.notification_sent.is_(False),
                )
            )
        )
        return list(result.scalars().all())

    async def mark_notified(self, expiry: ExpiryTracking) -> ExpiryTracking:
        return await self.update(
            expiry,
            notification_sent=True,
            notification_sent_at=datetime.now(timezone.utc),
        )

    async def get_by_inventory_item(
        self, inventory_item_id: UUID
    ) -> ExpiryTracking | None:
        result = await self.session.execute(
            select(ExpiryTracking).where(
                ExpiryTracking.inventory_item_id == inventory_item_id
            )
        )
        return result.scalar_one_or_none()
