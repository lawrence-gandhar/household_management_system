import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.unit import Unit


class CategoryUnit(UUIDMixin, TimestampMixin, Base):
    """
    Defines allowed units for a given category.

    Example:
        Category: Dairy
        Units: litre, millilitre, gram, kilogram

    This enables:
    - Category-specific measurement enforcement
    - Smart quantity validation
    - AI normalization rules
    """

    __tablename__ = "category_units"

    __table_args__ = (
        UniqueConstraint(
            "category_id",
            "unit_id",
            name="uq_category_units_category_unit",
        ),
        Index("ix_category_units_category_id", "category_id"),
        Index("ix_category_units_unit_id", "unit_id"),
    )

    # ── Foreign Keys ───────────────────────────────────────────

    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        nullable=False,
    )

    unit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="CASCADE"),
        nullable=False,
    )

    # ── Relationships ──────────────────────────────────────────

    category: Mapped["Category"] = relationship(
        "Category",
        back_populates="category_units",
        lazy="selectin",
    )

    unit: Mapped["Unit"] = relationship(
        "Unit",
        back_populates="category_units",
        lazy="selectin",
    )