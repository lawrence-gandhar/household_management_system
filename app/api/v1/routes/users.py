from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.equipment import EquipmentOut
from app.schemas.subscription import SubscriptionOut, SubscriptionUpgrade
from app.schemas.user import EquipmentIdList, UserOut, UserUpdate
from app.services.subscription import SubscriptionService
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=ApiResponse[UserOut])
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await UserService(db).get_profile(current_user.id)
    return ApiResponse(data=UserOut.model_validate(user))


@router.patch("/me", response_model=ApiResponse[UserOut])
async def update_profile(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await UserService(db).update_profile(current_user, payload)
    return ApiResponse(data=UserOut.model_validate(user))


@router.put("/me/equipment", response_model=ApiResponse[list[EquipmentOut]])
async def set_equipment(
    payload: EquipmentIdList,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = await UserService(db).set_equipment(current_user, payload.equipment_ids)
    equipment = [EquipmentOut.model_validate(eq) for eq in user.equipment]
    return ApiResponse(data=equipment)


# ── Subscription ─────────────────────────────────────────────────────────────

@router.get("/me/subscription", response_model=ApiResponse[SubscriptionOut])
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await SubscriptionService(db).get_subscription(current_user)
    return ApiResponse(data=sub)


@router.post("/me/subscription/upgrade", response_model=ApiResponse[SubscriptionOut])
async def upgrade_subscription(
    payload: SubscriptionUpgrade,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await SubscriptionService(db).upgrade_to_premium(current_user, payload)
    return ApiResponse(data=sub, message="Upgraded to premium")
