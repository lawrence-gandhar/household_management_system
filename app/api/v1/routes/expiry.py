from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.inventory import UpcomingExpiryOut
from app.services.expiry import ExpiryService

router = APIRouter(prefix="/expiry", tags=["Expiry Tracking"])


@router.get("/upcoming", response_model=ApiResponse[list[UpcomingExpiryOut]])
async def get_upcoming_expiries(
    days_ahead: int = Query(default=7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return items expiring within the next `days_ahead` days."""
    data = await ExpiryService(db).get_upcoming_expiries(current_user, days_ahead)
    return ApiResponse(data=data)
