from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

import uuid

if TYPE_CHECKING:
    from app.models.inventory import InventoryItem
    from app.models.recipe import Recipe
    from app.models.category_units import CategoryUnit


# ── Association tables (SQLAlchemy Core — no extra columns needed) ─────────────

recipe_categories = Table(
    "recipe_categories",
    Base.metadata,
    Column(
        "recipe_id",
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

inventory_item_categories = Table(
    "inventory_item_categories",
    Base.metadata,
    Column(
        "inventory_item_id",
        UUID(as_uuid=True),
        ForeignKey("inventory_items.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# ── ORM Model ──────────────────────────────────────────────────────────────────

class Category(UUIDMixin, TimestampMixin, Base):
    """Admin-managed hierarchical category catalog."""

    __tablename__ = "categories"

    __table_args__ = (
        Index("ix_categories_is_active_name", "is_active", "name"),
        Index(
            "ix_categories_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index("ix_categories_parent_id", "parent_id"),
    )

    # ── Core Fields ─────────────────────────────────────────
    name: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # ── Self-Referencing Hierarchy ─────────────────────────
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id", ondelete="SET NULL"),
        nullable=True,
    )

    parent: Mapped["Category | None"] = relationship(
        "Category",
        remote_side="Category.id",
        back_populates="children",
        lazy="selectin",
    )

    children: Mapped[list["Category"]] = relationship(
        "Category",
        back_populates="parent",
        lazy="noload",
    )

    # ── External Relationships ─────────────────────────────
    recipes: Mapped[list["Recipe"]] = relationship(
        "Recipe",
        secondary="recipe_categories",
        back_populates="categories",
        lazy="noload",
    )

    inventory_items: Mapped[list["InventoryItem"]] = relationship(
        "InventoryItem",
        secondary="inventory_item_categories",
        back_populates="categories",
        lazy="noload",
    )

    category_units: Mapped[list["CategoryUnit"]] = relationship(
        "CategoryUnit",
        back_populates="category",
        cascade="all, delete-orphan",
        lazy="noload",
    )

