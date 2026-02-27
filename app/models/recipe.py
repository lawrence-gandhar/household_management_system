import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.enums import RecipeDifficulty, RecipeSource
from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.user import User


class Recipe(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "recipes"

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        default=None,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, default=None)
    cuisine_type: Mapped[str | None] = mapped_column(String(100), index=True, default=None)
    prep_time_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    cook_time_minutes: Mapped[int | None] = mapped_column(Integer, default=None)
    servings: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    difficulty: Mapped[str] = mapped_column(
        Enum(RecipeDifficulty, name="recipe_difficulty"),
        default=RecipeDifficulty.medium,
        nullable=False,
    )
    source: Mapped[str] = mapped_column(
        Enum(RecipeSource, name="recipe_source"),
        default=RecipeSource.generated,
        nullable=False,
    )
    source_url: Mapped[str | None] = mapped_column(Text, default=None)
    instructions: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), default=None)
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User | None"] = relationship("User", back_populates="recipes")
    ingredients: Mapped[list["RecipeIngredient"]] = relationship(
        "RecipeIngredient", back_populates="recipe", cascade="all, delete-orphan"
    )
    categories: Mapped[list["Category"]] = relationship(
        "Category",
        secondary="recipe_categories",
        back_populates="recipes",
    )


class RecipeIngredient(UUIDMixin, Base):
    __tablename__ = "recipe_ingredients"

    recipe_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    quantity: Mapped[float | None] = mapped_column(Numeric(10, 2), default=None)
    unit: Mapped[str | None] = mapped_column(String(50), default=None)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, default=None)

    # Relationships
    recipe: Mapped["Recipe"] = relationship("Recipe", back_populates="ingredients")
