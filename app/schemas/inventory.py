import uuid
from datetime import date, datetime

from pydantic import Field

from app.core.enums import QuantityLevel
from app.schemas.common import OrmBase


class InventoryItemCreate(OrmBase):
    name: str = Field(max_length=255)
    category: str | None = Field(default=None, max_length=100)
    quantity: float | None = None
    quantity_unit: str | None = Field(default=None, max_length=50)
    quantity_level: QuantityLevel = QuantityLevel.full
    barcode: str | None = Field(default=None, max_length=100)
    brand: str | None = Field(default=None, max_length=255)
    is_packaged: bool = False
    notes: str | None = None
    expiry_date: date | None = None


class InventoryItemUpdate(OrmBase):
    name: str | None = Field(default=None, max_length=255)
    category: str | None = None
    quantity: float | None = None
    quantity_unit: str | None = None
    quantity_level: QuantityLevel | None = None
    barcode: str | None = None
    brand: str | None = None
    is_packaged: bool | None = None
    notes: str | None = None
    expiry_date: date | None = None


class ExpiryOut(OrmBase):
    id: uuid.UUID
    inventory_item_id: uuid.UUID
    expiry_date: date
    notification_sent: bool


class InventoryItemOut(OrmBase):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    category: str | None
    quantity: float | None
    quantity_unit: str | None
    quantity_level: QuantityLevel
    barcode: str | None
    brand: str | None
    image_url: str | None
    is_packaged: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
    expiry: ExpiryOut | None = None


class ScanRequest(OrmBase):
    scan_type: str = "packaged"


class UpcomingExpiryOut(OrmBase):
    inventory_item_id: uuid.UUID
    item_name: str
    expiry_date: date
    days_until_expiry: int
