# Import all models here so Alembic autogenerate can discover them.
# This file is the single source of truth for metadata.

from app.models.base import Base  # noqa: F401
from app.models.user import User, UserEquipmentAssociation  # noqa: F401
from app.models.subscription import Subscription  # noqa: F401
from app.models.equipment import Equipment, CuisineCategory  # noqa: F401
from app.models.inventory import InventoryItem, ExpiryTracking, AIScanLog  # noqa: F401
from app.models.recipe import Recipe, RecipeIngredient  # noqa: F401
from app.models.category import Category  # noqa: F401
from app.models.shopping_list import ShoppingList, ShoppingListItem  # noqa: F401
from app.models.auth import RevokedToken, EmailVerificationToken, PasswordResetToken  # noqa: F401
