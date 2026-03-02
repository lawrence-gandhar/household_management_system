import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin
from app.core.enums import UnitType  # You will create this enum

if TYPE_CHECKING:
    from app.models.category_units import CategoryUnit


class Unit(UUIDMixin, TimestampMixin, Base):
    """
    Represents measurable units used for inventory and recipes.

    Examples:
        gram (g)
        kilogram (kg)
        millilitre (mL)
        litre (L)
        piece (pc)
        pack (pk)

    Designed for:
    - Australian metric system
    - Quantity normalization
    - AI measurement mapping
    - Category-specific enforcement
    """

    __tablename__ = "units"

    __table_args__ = (
        UniqueConstraint("name", name="uq_units_name"),
        UniqueConstraint("short_code", name="uq_units_short_code"),
        Index("ix_units_type", "type"),
    )

    # ── Core Fields ─────────────────────────────────────────────

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    short_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    type: Mapped[UnitType] = mapped_column(
        Enum(UnitType, name="unit_type"),
        nullable=False,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # ── Optional Conversion Support (Future-Proofing) ───────────

    base_unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
    )

    conversion_factor: Mapped[Numeric | None] = mapped_column(
        Numeric(12, 6),
        nullable=True,
        default=None,
    )

    # ── Relationships ───────────────────────────────────────────

    category_units: Mapped[list["CategoryUnit"]] = relationship(
        "CategoryUnit",
        back_populates="unit",
        cascade="all, delete-orphan",
        lazy="noload",
    )