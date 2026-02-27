from fastapi import APIRouter

from app.api.v1.routes import auth, equipment, expiry, inventory, recipes, shopping_list, users

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(inventory.router)
api_router.include_router(recipes.router)
api_router.include_router(shopping_list.router)
api_router.include_router(equipment.router)
api_router.include_router(expiry.router)
