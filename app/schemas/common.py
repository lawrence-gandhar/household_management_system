from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

DataT = TypeVar("DataT")


class ApiResponse(BaseModel, Generic[DataT]):
    """Uniform JSON envelope for all API responses."""

    success: bool = True
    message: str = "OK"
    data: DataT | None = None


class PaginatedResponse(BaseModel, Generic[DataT]):
    success: bool = True
    total: int
    page: int
    page_size: int
    data: list[DataT]


class OrmBase(BaseModel):
    """Base schema for all ORM-mapped models."""

    model_config = ConfigDict(from_attributes=True)
