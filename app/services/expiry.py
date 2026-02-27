import logging
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.inventory import ExpiryRepository
from app.schemas.inventory import UpcomingExpiryOut

logger = logging.getLogger("pantry_mate.expiry")


class ExpiryService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = ExpiryRepository(db)

    async def get_upcoming_expiries(
        self, user: User, days_ahead: int = 7
    ) -> list[UpcomingExpiryOut]:
        records = await self._repo.get_upcoming(user.id, days_ahead=days_ahead)
        today = date.today()

        result = []
        for record in records:
            days_left = (record.expiry_date - today).days
            result.append(
                UpcomingExpiryOut(
                    inventory_item_id=record.inventory_item_id,
                    item_name=record.inventory_item.name,
                    expiry_date=record.expiry_date,
                    days_until_expiry=days_left,
                )
            )
        return result

    async def process_notifications(self) -> int:
        """
        Called by the background task scheduler.
        Marks notified records and triggers the notification channel
        (currently logs; extend to push / email / SMS as needed).
        Returns the count of notifications sent.
        """
        pending = await self._repo.get_pending_notifications()
        count = 0
        for record in pending:
            item_name = record.inventory_item.name if record.inventory_item else "Unknown"
            logger.info(
                "EXPIRY ALERT user_id=%s item='%s' expires=%s",
                record.user_id,
                item_name,
                record.expiry_date,
            )
            await self._repo.mark_notified(record)
            count += 1

        return count
