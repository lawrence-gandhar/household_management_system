from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.shopping_list import (
    ShoppingListCreate,
    ShoppingListItemCreate,
    ShoppingListItemOut,
    ShoppingListItemUpdate,
    ShoppingListOut,
    ShoppingListUpdate,
)
from app.services.shopping_list import ShoppingListService

router = APIRouter(prefix="/shopping-lists", tags=["Shopping Lists"])


@router.get("", response_model=ApiResponse[list[ShoppingListOut]])
async def list_shopping_lists(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    lists = await ShoppingListService(db).list_shopping_lists(current_user)
    return ApiResponse(data=[ShoppingListOut.model_validate(sl) for sl in lists])


@router.post("", response_model=ApiResponse[ShoppingListOut], status_code=201)
async def create_shopping_list(
    payload: ShoppingListCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sl = await ShoppingListService(db).create_shopping_list(current_user, payload)
    return ApiResponse(data=ShoppingListOut.model_validate(sl))


@router.get("/{list_id}", response_model=ApiResponse[ShoppingListOut])
async def get_shopping_list(
    list_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sl = await ShoppingListService(db).get_shopping_list(current_user, list_id)
    return ApiResponse(data=ShoppingListOut.model_validate(sl))


@router.patch("/{list_id}", response_model=ApiResponse[ShoppingListOut])
async def update_shopping_list(
    list_id: UUID,
    payload: ShoppingListUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sl = await ShoppingListService(db).update_shopping_list(current_user, list_id, payload)
    return ApiResponse(data=ShoppingListOut.model_validate(sl))


@router.delete("/{list_id}", response_model=ApiResponse[None])
async def delete_shopping_list(
    list_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ShoppingListService(db).delete_shopping_list(current_user, list_id)
    return ApiResponse(message="Shopping list deleted")


@router.post("/{list_id}/from-recipe/{recipe_id}", response_model=ApiResponse[ShoppingListOut])
async def generate_from_recipe(
    list_id: UUID,
    recipe_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a new shopping list pre-filled from a recipe's ingredients."""
    sl = await ShoppingListService(db).generate_from_recipe(current_user, recipe_id)
    return ApiResponse(data=ShoppingListOut.model_validate(sl))


# ── Items ─────────────────────────────────────────────────────────────────────

@router.post("/{list_id}/items", response_model=ApiResponse[ShoppingListItemOut], status_code=201)
async def add_item(
    list_id: UUID,
    payload: ShoppingListItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await ShoppingListService(db).add_item(current_user, list_id, payload)
    return ApiResponse(data=ShoppingListItemOut.model_validate(item))


@router.patch("/{list_id}/items/{item_id}", response_model=ApiResponse[ShoppingListItemOut])
async def update_item(
    list_id: UUID,
    item_id: UUID,
    payload: ShoppingListItemUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await ShoppingListService(db).update_item(
        current_user, list_id, item_id, payload
    )
    return ApiResponse(data=ShoppingListItemOut.model_validate(item))


@router.delete("/{list_id}/items/{item_id}", response_model=ApiResponse[None])
async def delete_item(
    list_id: UUID,
    item_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ShoppingListService(db).delete_item(current_user, list_id, item_id)
    return ApiResponse(message="Item removed")
