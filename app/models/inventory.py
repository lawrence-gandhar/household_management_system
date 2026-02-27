import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import QuantityLevel, ScanStatus, ScanType
from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.user import User


class InventoryItem(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "inventory_items"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(100), index=True, default=None)
    quantity: Mapped[float | None] = mapped_column(Numeric(10, 2), default=None)
    quantity_unit: Mapped[str | None] = mapped_column(String(50), default=None)
    quantity_level: Mapped[str] = mapped_column(
        Enum(QuantityLevel, name="quantity_level"),
        default=QuantityLevel.full,
        nullable=False,
    )
    barcode: Mapped[str | None] = mapped_column(String(100), index=True, default=None)
    brand: Mapped[str | None] = mapped_column(String(255), default=None)
    image_url: Mapped[str | None] = mapped_column(Text, default=None)
    is_packaged: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="inventory_items")
    categories: Mapped[list["Category"]] = relationship(
        "Category",
        secondary="inventory_item_categories",
        back_populates="inventory_items",
    )
    expiry: Mapped["ExpiryTracking | None"] = relationship(
        "ExpiryTracking", back_populates="inventory_item", uselist=False,
        cascade="all, delete-orphan",
    )


class ExpiryTracking(UUIDMixin, Base):
    __tablename__ = "expiry_tracking"

    inventory_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expiry_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    notification_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )

    # Relationships
    inventory_item: Mapped["InventoryItem"] = relationship(
        "InventoryItem", back_populates="expiry"
    )


class AIScanLog(UUIDMixin, Base):
    __tablename__ = "ai_scan_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scan_type: Mapped[str] = mapped_column(
        Enum(ScanType, name="scan_type"), nullable=False
    )
    image_url: Mapped[str | None] = mapped_column(Text, default=None)
    result: Mapped[dict | None] = mapped_column(JSON, default=None)
    status: Mapped[str] = mapped_column(
        Enum(ScanStatus, name="scan_status"),
        default=ScanStatus.pending,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default="now()"
    )
