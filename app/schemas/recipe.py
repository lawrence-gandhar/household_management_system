import uuid
from datetime import datetime

from pydantic import Field

from app.core.enums import RecipeDifficulty, RecipeSource
from app.schemas.common import OrmBase


class RecipeIngredientCreate(OrmBase):
    name: str = Field(max_length=255)
    quantity: float | None = None
    unit: str | None = Field(default=None, max_length=50)
    is_optional: bool = False
    notes: str | None = None


class RecipeIngredientOut(OrmBase):
    id: uuid.UUID
    name: str
    quantity: float | None
    unit: str | None
    is_optional: bool


class RecipeCreate(OrmBase):
    title: str = Field(max_length=255)
    description: str | None = None
    cuisine_type: str | None = Field(default=None, max_length=100)
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None
    servings: int = 2
    difficulty: RecipeDifficulty = RecipeDifficulty.medium
    source: RecipeSource = RecipeSource.manual
    source_url: str | None = None
    instructions: str
    tags: list[str] | None = None
    ingredients: list[RecipeIngredientCreate] = []


class RecipeOut(OrmBase):
    id: uuid.UUID
    user_id: uuid.UUID | None
    title: str
    description: str | None
    cuisine_type: str | None
    prep_time_minutes: int | None
    cook_time_minutes: int | None
    servings: int
    difficulty: RecipeDifficulty
    source: RecipeSource
    source_url: str | None
    instructions: str
    tags: list[str] | None
    is_premium: bool
    created_at: datetime
    ingredients: list[RecipeIngredientOut] = []


class RecipeGenerateRequest(OrmBase):
    cuisine_preference: str | None = None
    time_constraint_minutes: int | None = None
    count: int = Field(default=1, ge=1, le=10)


class RecipeImportRequest(OrmBase):
    url: str = Field(min_length=10, max_length=2048)
