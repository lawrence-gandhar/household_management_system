from uuid import UUID

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.enums import ScanStatus, ScanType, SubscriptionTier
from app.core.exceptions import NotFoundException, PaymentRequiredException
from app.integrations.ai_scanner import ScanResult, get_ai_scanner
from app.models.inventory import InventoryItem
from app.models.user import User
from app.repositories.inventory import ExpiryRepository, InventoryRepository
from app.schemas.inventory import InventoryItemCreate, InventoryItemOut, InventoryItemUpdate


class InventoryService:
    def __init__(self, db: AsyncSession) -> None:
        self._repo = InventoryRepository(db)
        self._expiry_repo = ExpiryRepository(db)
        self._db = db

    # ── Tier enforcement ────────────────────────────────────────────────────

    async def _enforce_free_limit(self, user: User) -> None:
        sub = user.subscription
        if sub is not None and sub.tier == SubscriptionTier.premium:
            return
        count = await self._repo.count_by_user(user.id)
        if count >= settings.FREE_INVENTORY_LIMIT:
            raise PaymentRequiredException(
                f"Free tier is limited to {settings.FREE_INVENTORY_LIMIT} items. "
                "Upgrade to premium for unlimited inventory."
            )

    # ── CRUD ────────────────────────────────────────────────────────────────

    async def list_items(
        self, user: User, skip: int = 0, limit: int = 100
    ) -> list[InventoryItem]:
        return await self._repo.get_by_user(user.id, skip=skip, limit=limit)

    async def get_item(self, user: User, item_id: UUID) -> InventoryItem:
        item = await self._repo.get_by_user_and_id(user.id, item_id)
        if not item:
            raise NotFoundException("Inventory item not found")
        return item

    async def add_item(self, user: User, data: InventoryItemCreate) -> InventoryItem:
        await self._enforce_free_limit(user)

        expiry_date = data.expiry_date
        item_data = data.model_dump(exclude={"expiry_date"})
        item = await self._repo.create(user_id=user.id, **item_data)

        if expiry_date:
            await self._expiry_repo.create(
                inventory_item_id=item.id,
                user_id=user.id,
                expiry_date=expiry_date,
            )
            await self._db.refresh(item)

        return item

    async def update_item(
        self, user: User, item_id: UUID, data: InventoryItemUpdate
    ) -> InventoryItem:
        item = await self.get_item(user, item_id)

        expiry_date = data.expiry_date
        update_data = data.model_dump(
            exclude_none=True, exclude_unset=True, exclude={"expiry_date"}
        )
        if update_data:
            item = await self._repo.update(item, **update_data)

        if expiry_date is not None:
            existing_expiry = await self._expiry_repo.get_by_inventory_item(item.id)
            if existing_expiry:
                await self._expiry_repo.update(
                    existing_expiry, expiry_date=expiry_date, notification_sent=False
                )
            else:
                await self._expiry_repo.create(
                    inventory_item_id=item.id,
                    user_id=user.id,
                    expiry_date=expiry_date,
                )
            await self._db.refresh(item)

        return item

    async def delete_item(self, user: User, item_id: UUID) -> None:
        item = await self.get_item(user, item_id)
        await self._repo.delete(item)

    # ── AI Scan ─────────────────────────────────────────────────────────────

    async def scan_and_add(
        self, user: User, file: UploadFile, scan_type: str = "packaged"
    ) -> InventoryItem:
        await self._enforce_free_limit(user)

        image_bytes = await file.read()
        scanner = get_ai_scanner()

        if scan_type == ScanType.packaged:
            result: ScanResult = await scanner.scan_packaged(image_bytes)
        else:
            result = await scanner.scan_fresh(image_bytes)

        item_data = InventoryItemCreate(
            name=result.name,
            quantity_level=result.quantity_level,
            barcode=result.barcode,
            is_packaged=result.is_packaged,
        )
        return await self.add_item(user, item_data)
