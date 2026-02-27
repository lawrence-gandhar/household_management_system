import uuid
from datetime import datetime

from app.core.enums import SubscriptionTier
from app.schemas.common import OrmBase


class SubscriptionOut(OrmBase):
    id: uuid.UUID
    user_id: uuid.UUID
    tier: SubscriptionTier
    starts_at: datetime
    expires_at: datetime | None
    is_active: bool
    created_at: datetime


class SubscriptionUpgrade(OrmBase):
    payment_reference: str | None = None
