import uuid

from pydantic import Field

from app.schemas.common import OrmBase


class EquipmentCreate(OrmBase):
    name: str = Field(max_length=255)
    description: str | None = None
    category: str | None = Field(default=None, max_length=100)


class EquipmentUpdate(OrmBase):
    name: str | None = Field(default=None, max_length=255)
    description: str | None = None
    category: str | None = None
    is_active: bool | None = None


class EquipmentOut(OrmBase):
    id: uuid.UUID
    name: str
    description: str | None
    category: str | None
    is_active: bool


class CuisineCategoryCreate(OrmBase):
    name: str = Field(max_length=100)
    description: str | None = None


class CuisineCategoryOut(OrmBase):
    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
