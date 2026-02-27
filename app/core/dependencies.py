from uuid import UUID

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenException, PaymentRequiredException, UnauthorizedException
from app.core.security import decode_token
from app.db.session import get_db

_bearer = HTTPBearer()


async def get_token_payload(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> dict:
    """Decode and validate the Bearer access token.

    Returns the raw JWT payload dict so callers (e.g. the logout route) can
    access claims like ``jti`` and ``exp`` directly.

    Raises :class:`~app.core.exceptions.UnauthorizedException` on any failure.
    """
    try:
        payload = decode_token(credentials.credentials)
        if payload.get("type") != "access":
            raise UnauthorizedException("Invalid token type")
        return payload
    except (JWTError, KeyError):
        raise UnauthorizedException()


async def get_current_user(
    payload: dict = Depends(get_token_payload),
    db: AsyncSession = Depends(get_db),
):
    """Resolve the authenticated :class:`~app.models.user.User` from the Bearer token.

    Checks:
    1. Token type is ``"access"`` (enforced in :func:`get_token_payload`).
    2. The token's ``jti`` is not in the revoked-token blacklist.
    3. The user exists and ``is_active`` is ``True``.
    """
    # Import inside function to avoid circular imports at module load time
    from app.repositories.auth import RevokedTokenRepository
    from app.repositories.user import UserRepository

    jti: str | None = payload.get("jti")

    # Check jti blacklist on every authenticated request
    if jti and await RevokedTokenRepository(db).is_revoked(jti):
        raise UnauthorizedException("Token has been revoked")

    try:
        user_id = UUID(payload["sub"])
    except (KeyError, ValueError):
        raise UnauthorizedException()

    # Use get_with_subscription so subscription tier is always available
    # without an extra query inside require_premium / service layer.
    user = await UserRepository(db).get_with_subscription(user_id)

    if user is None or not user.is_active:
        raise UnauthorizedException("User not found or deactivated")

    return user


async def get_current_admin(current_user=Depends(get_current_user)):
    """Raise 403 if the authenticated user is not an admin."""
    from app.core.enums import UserRole

    if current_user.role != UserRole.admin:
        raise ForbiddenException("Admin access required")
    return current_user


async def require_premium(current_user=Depends(get_current_user)):
    """Raise 402 if the authenticated user is on the free tier.

    Tier is read from the eagerly-loaded ``subscription`` relationship.
    Admins always bypass tier enforcement.
    """
    from app.core.enums import SubscriptionTier, UserRole

    sub = current_user.subscription
    is_premium = sub is not None and sub.tier == SubscriptionTier.premium
    is_admin = current_user.role == UserRole.admin
    if not (is_premium or is_admin):
        raise PaymentRequiredException()
    return current_user
