from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin, get_current_user
from app.db.session import get_db
from app.models.equipment import CuisineCategory, Equipment
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.equipment import (
    CuisineCategoryCreate,
    CuisineCategoryOut,
    EquipmentCreate,
    EquipmentOut,
    EquipmentUpdate,
)

router = APIRouter(prefix="/equipment", tags=["Equipment"])


# ── Public catalog ────────────────────────────────────────────────────────────

@router.get("", response_model=ApiResponse[list[EquipmentOut]])
async def list_equipment(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Equipment).where(Equipment.is_active.is_(True)))
    items = result.scalars().all()
    return ApiResponse(data=[EquipmentOut.model_validate(e) for e in items])


@router.get("/cuisine-categories", response_model=ApiResponse[list[CuisineCategoryOut]])
async def list_cuisine_categories(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(CuisineCategory).where(CuisineCategory.is_active.is_(True))
    )
    items = result.scalars().all()
    return ApiResponse(data=[CuisineCategoryOut.model_validate(c) for c in items])


# ── Admin-only management ─────────────────────────────────────────────────────

@router.post("", response_model=ApiResponse[EquipmentOut], status_code=201)
async def create_equipment(
    payload: EquipmentCreate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    eq = Equipment(**payload.model_dump())
    db.add(eq)
    await db.flush()
    await db.refresh(eq)
    return ApiResponse(data=EquipmentOut.model_validate(eq))


@router.patch("/{equipment_id}", response_model=ApiResponse[EquipmentOut])
async def update_equipment(
    equipment_id: UUID,
    payload: EquipmentUpdate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Equipment).where(Equipment.id == equipment_id))
    eq = result.scalar_one_or_none()
    if not eq:
        from app.core.exceptions import NotFoundException
        raise NotFoundException("Equipment not found")
    for k, v in payload.model_dump(exclude_none=True, exclude_unset=True).items():
        setattr(eq, k, v)
    await db.flush()
    await db.refresh(eq)
    return ApiResponse(data=EquipmentOut.model_validate(eq))


@router.post("/cuisine-categories", response_model=ApiResponse[CuisineCategoryOut], status_code=201)
async def create_cuisine_category(
    payload: CuisineCategoryCreate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    cat = CuisineCategory(**payload.model_dump())
    db.add(cat)
    await db.flush()
    await db.refresh(cat)
    return ApiResponse(data=CuisineCategoryOut.model_validate(cat))
