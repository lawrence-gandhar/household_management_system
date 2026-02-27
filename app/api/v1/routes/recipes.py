from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, require_premium
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.recipe import RecipeGenerateRequest, RecipeImportRequest, RecipeOut
from app.services.recipe import RecipeService

router = APIRouter(prefix="/recipes", tags=["Recipes"])


@router.get("", response_model=ApiResponse[list[RecipeOut]])
async def list_recipes(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    recipes = await RecipeService(db).list_recipes(current_user, skip=skip, limit=limit)
    return ApiResponse(data=[RecipeOut.model_validate(r) for r in recipes])


@router.get("/{recipe_id}", response_model=ApiResponse[RecipeOut])
async def get_recipe(
    recipe_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    recipe = await RecipeService(db).get_recipe(current_user, recipe_id)
    return ApiResponse(data=RecipeOut.model_validate(recipe))


@router.post("/generate", response_model=ApiResponse[list[RecipeOut]])
async def generate_recipes(
    payload: RecipeGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate recipe suggestions from the user's current inventory.
    Free tier: max 1 recipe. Premium: up to `count` recipes.
    """
    recipes = await RecipeService(db).generate_from_inventory(current_user, payload)
    return ApiResponse(data=[RecipeOut.model_validate(r) for r in recipes])


@router.post("/import", response_model=ApiResponse[RecipeOut], status_code=201)
async def import_recipe(
    payload: RecipeImportRequest,
    current_user: User = Depends(require_premium),   # blocks free tier
    db: AsyncSession = Depends(get_db),
):
    """Premium only: parse and import a recipe from a URL."""
    recipe = await RecipeService(db).import_from_url(current_user, payload)
    return ApiResponse(
        data=RecipeOut.model_validate(recipe),
        message="Recipe imported successfully",
    )


@router.delete("/{recipe_id}", response_model=ApiResponse[None])
async def delete_recipe(
    recipe_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await RecipeService(db).delete_recipe(current_user, recipe_id)
    return ApiResponse(message="Recipe deleted")
