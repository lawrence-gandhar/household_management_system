from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.enums import SubscriptionTier
from app.core.exceptions import NotFoundException
from app.models.user import User
from app.repositories.subscription import SubscriptionRepository
from app.schemas.subscription import SubscriptionOut, SubscriptionUpgrade


class SubscriptionService:
    def __init__(self, db: AsyncSession) -> None:
        self._sub_repo = SubscriptionRepository(db)

    async def get_subscription(self, user: User) -> SubscriptionOut:
        sub = await self._sub_repo.get_by_user_id(user.id)
        if not sub:
            raise NotFoundException("Subscription not found")
        return SubscriptionOut.model_validate(sub)

    async def upgrade_to_premium(
        self, user: User, data: SubscriptionUpgrade
    ) -> SubscriptionOut:
        sub = await self._sub_repo.get_by_user_id(user.id)
        if not sub:
            raise NotFoundException("Subscription not found")

        expires_at = datetime.now(timezone.utc) + timedelta(days=365)

        sub = await self._sub_repo.upgrade_to_premium(
            sub,
            payment_reference=data.payment_reference,
            expires_at=expires_at,
        )

        return SubscriptionOut.model_validate(sub)

    async def downgrade_to_free(self, user: User) -> SubscriptionOut:
        sub = await self._sub_repo.get_by_user_id(user.id)
        if not sub:
            raise NotFoundException("Subscription not found")

        sub = await self._sub_repo.update(
            sub,
            tier=SubscriptionTier.free,
            expires_at=None,
            payment_reference=None,
        )
        return SubscriptionOut.model_validate(sub)
