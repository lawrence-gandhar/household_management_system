from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Column, ForeignKey, Index, String, Table, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.inventory import InventoryItem
    from app.models.recipe import Recipe


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
    """Admin-managed category catalog shared across recipes and inventory items."""

    __tablename__ = "categories"

    # ── Indexes ───────────────────────────────────────────────────────────────
    # ix_categories_is_active_name: covers the dominant admin list query
    #   SELECT … WHERE is_active = TRUE ORDER BY name
    #   (index-only scan for filter + sort; no heap fetch needed for bool+varchar).
    #
    # ix_categories_name_trgm: GIN trigram index that turns admin LIKE '%term%'
    #   searches on 100k+ rows from sequential scans into sub-millisecond lookups.
    #   Requires the pg_trgm extension — add to your migration with:
    #       op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    __table_args__ = (
        Index("ix_categories_is_active_name", "is_active", "name"),
        Index(
            "ix_categories_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, default=None)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships — lazy="noload" prevents accidental O(N) eager fetches
    # in the admin list view; load explicitly when needed via selectinload().
    recipes: Mapped[list["Recipe"]] = relationship(
        "Recipe",
        secondary=recipe_categories,
        back_populates="categories",
        lazy="noload",
    )
    inventory_items: Mapped[list["InventoryItem"]] = relationship(
        "InventoryItem",
        secondary=inventory_item_categories,
        back_populates="categories",
        lazy="noload",
    )
