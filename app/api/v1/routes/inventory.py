from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.inventory import InventoryItemCreate, InventoryItemOut, InventoryItemUpdate
from app.services.inventory import InventoryService

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.get("", response_model=ApiResponse[list[InventoryItemOut]])
async def list_inventory(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    items = await InventoryService(db).list_items(current_user, skip=skip, limit=limit)
    return ApiResponse(data=[InventoryItemOut.model_validate(i) for i in items])


@router.post("", response_model=ApiResponse[InventoryItemOut], status_code=201)
async def add_inventory_item(
    payload: InventoryItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await InventoryService(db).add_item(current_user, payload)
    return ApiResponse(data=InventoryItemOut.model_validate(item), status_code=201)


@router.get("/{item_id}", response_model=ApiResponse[InventoryItemOut])
async def get_inventory_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await InventoryService(db).get_item(current_user, item_id)
    return ApiResponse(data=InventoryItemOut.model_validate(item))


@router.patch("/{item_id}", response_model=ApiResponse[InventoryItemOut])
async def update_inventory_item(
    item_id: UUID,
    payload: InventoryItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await InventoryService(db).update_item(current_user, item_id, payload)
    return ApiResponse(data=InventoryItemOut.model_validate(item))


@router.delete("/{item_id}", response_model=ApiResponse[None])
async def delete_inventory_item(
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await InventoryService(db).delete_item(current_user, item_id)
    return ApiResponse(message="Item deleted")


@router.post("/scan", response_model=ApiResponse[InventoryItemOut], status_code=201)
async def scan_image(
    file: UploadFile = File(...),
    scan_type: str = Query(default="packaged", pattern="^(packaged|fresh)$"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload an image to automatically detect and add a pantry item."""
    item = await InventoryService(db).scan_and_add(current_user, file, scan_type)
    return ApiResponse(
        data=InventoryItemOut.model_validate(item),
        message="Item detected and added",
    )
