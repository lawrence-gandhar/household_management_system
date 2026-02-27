from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubscriptionTier
from app.models.subscription import Subscription
from app.repositories.base import BaseRepository


class SubscriptionRepository(BaseRepository[Subscription]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Subscription, session)

    async def get_by_user_id(self, user_id: UUID) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription).where(Subscription.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_free(self, user_id: UUID) -> Subscription:
        return await self.create(
            user_id=user_id,
            tier=SubscriptionTier.free,
            starts_at=datetime.now(timezone.utc),
        )

    async def upgrade_to_premium(
        self,
        subscription: Subscription,
        payment_reference: str | None = None,
        expires_at: datetime | None = None,
    ) -> Subscription:
        return await self.update(
            subscription,
            tier=SubscriptionTier.premium,
            is_active=True,
            payment_reference=payment_reference,
            expires_at=expires_at,
        )
