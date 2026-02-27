import uuid
from datetime import datetime

from pydantic import Field

from app.schemas.common import OrmBase


class ShoppingListItemCreate(OrmBase):
    ingredient_name: str = Field(max_length=255)
    quantity: float | None = None
    unit: str | None = Field(default=None, max_length=50)
    notes: str | None = None


class ShoppingListItemUpdate(OrmBase):
    ingredient_name: str | None = None
    quantity: float | None = None
    unit: str | None = None
    is_purchased: bool | None = None
    notes: str | None = None


class ShoppingListItemOut(OrmBase):
    id: uuid.UUID
    ingredient_name: str
    quantity: float | None
    unit: str | None
    is_purchased: bool
    notes: str | None


class ShoppingListCreate(OrmBase):
    title: str = Field(default="Shopping List", max_length=255)
    items: list[ShoppingListItemCreate] = []


class ShoppingListUpdate(OrmBase):
    title: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class ShoppingListOut(OrmBase):
    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    items: list[ShoppingListItemOut] = []
