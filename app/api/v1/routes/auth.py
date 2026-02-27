"""Auth endpoints.

Public:
  POST /auth/register          — create account, returns token pair
  POST /auth/login             — credential login, returns token pair
  POST /auth/refresh           — rotate refresh token, returns new token pair
  GET  /auth/verify-email      — consume email-verification link
  POST /auth/forgot-password   — request a password-reset email
  POST /auth/reset-password    — consume reset token, set new password

Protected (requires Bearer token):
  POST /auth/logout            — revoke current access + refresh tokens
  POST /auth/change-password   — update password (current + new)
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_token_payload
from app.db.session import get_db
from app.schemas.common import ApiResponse
from app.schemas.user import (
    ForgotPasswordRequest,
    PasswordChange,
    ResetPasswordRequest,
    TokenPair,
    TokenRefresh,
    UserCreate,
    UserLogin,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Public endpoints ──────────────────────────────────────────────────────────

@router.post("/register", response_model=ApiResponse[TokenPair], status_code=201)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """Create a new user account and return a JWT token pair."""
    tokens = await AuthService(db).register(payload)
    return ApiResponse(data=tokens, message="Account created successfully")


@router.post("/login", response_model=ApiResponse[TokenPair])
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticate with email + password and return a JWT token pair."""
    tokens = await AuthService(db).login(payload.email, payload.password)
    return ApiResponse(data=tokens)


@router.post("/refresh", response_model=ApiResponse[TokenPair])
async def refresh(payload: TokenRefresh, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new token pair (refresh is rotated)."""
    tokens = await AuthService(db).refresh(payload.refresh_token)
    return ApiResponse(data=tokens)


@router.get("/verify-email", response_model=ApiResponse[None])
async def verify_email(
    token: str = Query(..., description="Email-verification token from the link"),
    db: AsyncSession = Depends(get_db),
):
    """Consume the one-time email-verification token sent after registration."""
    await AuthService(db).verify_email(token)
    return ApiResponse(message="Email verified successfully")


@router.post("/forgot-password", response_model=ApiResponse[None])
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Request a password-reset link sent to the registered email address.

    Always returns 200 — even when the email is not registered — to prevent
    user-enumeration attacks.
    """
    await AuthService(db).forgot_password(payload)
    return ApiResponse(
        message="If that email is registered you will receive a reset link shortly"
    )


@router.post("/reset-password", response_model=ApiResponse[None])
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Consume a password-reset token and update the account password."""
    await AuthService(db).reset_password(payload)
    return ApiResponse(message="Password has been reset successfully")


# ── Protected endpoints ───────────────────────────────────────────────────────

@router.post("/logout", response_model=ApiResponse[None])
async def logout(
    payload: TokenRefresh,
    token_payload: dict = Depends(get_token_payload),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke the current access token and the supplied refresh token.

    Both tokens are added to the JWT blacklist immediately; any subsequent
    request using either token will receive a 401.
    """
    access_jti: str = token_payload.get("jti", "")
    access_expires_at = datetime.fromtimestamp(token_payload["exp"], tz=timezone.utc)

    await AuthService(db).logout(
        user_id=current_user.id,
        access_jti=access_jti,
        access_expires_at=access_expires_at,
        refresh_token=payload.refresh_token,
    )
    return ApiResponse(message="Logged out successfully")


@router.post("/change-password", response_model=ApiResponse[None])
async def change_password(
    payload: PasswordChange,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the authenticated user's password (requires current password)."""
    await AuthService(db).change_password(current_user.id, payload)
    return ApiResponse(message="Password changed successfully")
