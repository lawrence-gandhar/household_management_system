import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from app.core.enums import UserRole
from app.schemas.common import OrmBase


class UserCreate(OrmBase):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


class UserLogin(OrmBase):
    email: EmailStr
    password: str


class UserUpdate(OrmBase):
    full_name: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None


class UserOut(OrmBase):
    id: uuid.UUID
    email: str
    full_name: str | None
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime


class TokenPair(OrmBase):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefresh(OrmBase):
    refresh_token: str


class EquipmentIdList(OrmBase):
    equipment_ids: list[uuid.UUID]


# ── Auth action schemas ───────────────────────────────────────────────────────

class PasswordChange(OrmBase):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class ForgotPasswordRequest(OrmBase):
    email: EmailStr


class ResetPasswordRequest(OrmBase):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
