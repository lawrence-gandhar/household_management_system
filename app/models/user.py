import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import UserRole
from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.equipment import Equipment
    from app.models.inventory import InventoryItem
    from app.models.recipe import Recipe
    from app.models.shopping_list import ShoppingList
    from app.models.subscription import Subscription


class User(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), default=None)
    role: Mapped[str] = mapped_column(
        Enum(UserRole, name="user_role"),
        default=UserRole.user,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    subscription: Mapped["Subscription | None"] = relationship(
        "Subscription", back_populates="user", cascade="all, delete-orphan"
    )
    equipment: Mapped[list["Equipment"]] = relationship(
        "Equipment", secondary="user_equipment", back_populates="users"
    )
    inventory_items: Mapped[list["InventoryItem"]] = relationship(
        "InventoryItem", back_populates="user", cascade="all, delete-orphan"
    )
    recipes: Mapped[list["Recipe"]] = relationship(
        "Recipe", back_populates="user", cascade="all, delete-orphan"
    )
    shopping_lists: Mapped[list["ShoppingList"]] = relationship(
        "ShoppingList", back_populates="user", cascade="all, delete-orphan"
    )


class UserEquipmentAssociation(Base):
    """Junction table — kept here to avoid circular imports with Equipment model."""

    __tablename__ = "user_equipment"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    equipment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("equipment.id", ondelete="CASCADE"),
        primary_key=True,
    )
