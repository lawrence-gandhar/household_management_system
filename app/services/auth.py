"""Authentication service.

Covers the complete auth lifecycle:
  - register        — create user + free subscription + email-verification token
  - login           — credential check → token pair
  - logout          — revoke the active access *and* refresh token by jti
  - refresh         — rotate refresh token (revoke old, issue new pair)
  - verify_email    — consume the email-verification token
  - forgot_password — generate + "send" a password-reset token
  - reset_password  — consume the reset token, update password
  - change_password — verify current password, update to new one
"""

import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictException,
    ForbiddenException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_secure_token,
    hash_password,
    verify_password,
)
from app.repositories.auth import (
    PasswordResetTokenRepository,
    RevokedTokenRepository,
    VerificationTokenRepository,
)
from app.repositories.subscription import SubscriptionRepository
from app.repositories.user import UserRepository
from app.schemas.user import (
    ForgotPasswordRequest,
    PasswordChange,
    ResetPasswordRequest,
    TokenPair,
    UserCreate,
)

logger = logging.getLogger(__name__)

# TTL for out-of-band one-time tokens
_EMAIL_VERIFY_TTL = timedelta(hours=24)
_PASSWORD_RESET_TTL = timedelta(hours=1)


def _make_pair(access, refresh) -> TokenPair:
    """Build a :class:`TokenPair` from two :class:`~app.core.security.CreatedToken` values."""
    return TokenPair(access_token=access.token, refresh_token=refresh.token)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._user_repo = UserRepository(db)
        self._sub_repo = SubscriptionRepository(db)
        self._revoked_repo = RevokedTokenRepository(db)
        self._verify_repo = VerificationTokenRepository(db)
        self._reset_repo = PasswordResetTokenRepository(db)

    # ── Registration ──────────────────────────────────────────────────────────

    async def register(self, data: UserCreate) -> TokenPair:
        """Create a new account, provision a free subscription, and return a token pair.

        An email-verification token is generated and the link is logged —
        replace the ``logger.info`` call with your email-sending integration.
        """
        if await self._user_repo.email_exists(data.email):
            raise ConflictException("An account with this email already exists")

        user = await self._user_repo.create(
            email=data.email,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
        )
        await self._sub_repo.create_free(user.id)

        # Generate an email-verification token (does not block login)
        verify_tok = generate_secure_token()
        await self._verify_repo.create(
            user_id=user.id,
            token=verify_tok,
            expires_at=datetime.now(timezone.utc) + _EMAIL_VERIFY_TTL,
        )
        logger.info(
            "Email verification link for %s → /api/v1/auth/verify-email?token=%s",
            user.email,
            verify_tok,
        )

        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)
        return _make_pair(access, refresh)

    # ── Login ─────────────────────────────────────────────────────────────────

    async def login(self, email: str, password: str) -> TokenPair:
        user = await self._user_repo.get_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            raise UnauthorizedException("Invalid email or password")
        if not user.is_active:
            raise ForbiddenException("Account is deactivated")

        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)
        return _make_pair(access, refresh)

    # ── Logout ────────────────────────────────────────────────────────────────

    async def logout(
        self,
        user_id: UUID,
        access_jti: str,
        access_expires_at: datetime,
        refresh_token: str,
    ) -> None:
        """Blacklist the current access token and (best-effort) the refresh token.

        After this call both jtis are in the revoked table and will be rejected
        by :func:`~app.core.dependencies.get_current_user` on every subsequent request.
        """
        await self._revoked_repo.revoke(
            jti=access_jti,
            user_id=user_id,
            token_type="access",
            expires_at=access_expires_at,
        )

        # Best-effort revocation of the refresh token
        try:
            rp = decode_token(refresh_token)
            if rp.get("type") == "refresh" and rp.get("jti"):
                await self._revoked_repo.revoke(
                    jti=rp["jti"],
                    user_id=user_id,
                    token_type="refresh",
                    expires_at=datetime.fromtimestamp(rp["exp"], tz=timezone.utc),
                )
        except (JWTError, KeyError, ValueError):
            # An invalid refresh token during logout is harmless; access is already revoked
            pass

    # ── Token refresh with rotation ───────────────────────────────────────────

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Issue a new token pair and rotate (revoke) the old refresh token.

        Replay-attack guard: if the presented jti is already revoked the
        request is rejected, regardless of token expiry.
        """
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise UnauthorizedException("Invalid token type")
            user_id = UUID(payload["sub"])
            old_jti: str = payload["jti"]
            old_expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        except (JWTError, KeyError, ValueError):
            raise UnauthorizedException("Invalid or expired refresh token")

        if await self._revoked_repo.is_revoked(old_jti):
            raise UnauthorizedException("Refresh token has already been used or revoked")

        user = await self._user_repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise UnauthorizedException("User not found or deactivated")

        # Revoke the old jti before issuing the replacement
        await self._revoked_repo.revoke(
            jti=old_jti,
            user_id=user_id,
            token_type="refresh",
            expires_at=old_expires_at,
        )

        access = create_access_token(user.id)
        new_refresh = create_refresh_token(user.id)
        return _make_pair(access, new_refresh)

    # ── Email verification ────────────────────────────────────────────────────

    async def verify_email(self, token: str) -> None:
        """Mark the user's email as verified and consume the one-time token."""
        entry = await self._verify_repo.get_by_token(token)
        if entry is None:
            raise UnauthorizedException("Invalid or expired verification link")

        expires = entry.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            await self._verify_repo.delete(entry)
            raise UnauthorizedException("Verification link has expired — request a new one")

        user = await self._user_repo.get_by_id(entry.user_id)
        if user is None:
            raise UnauthorizedException("User not found")

        await self._user_repo.update(user, is_verified=True)
        await self._verify_repo.delete(entry)

    # ── Password reset ────────────────────────────────────────────────────────

    async def forgot_password(self, data: ForgotPasswordRequest) -> None:
        """Generate a password-reset token and log the link.

        Succeeds silently even when the email is not registered to prevent
        user-enumeration attacks.
        """
        user = await self._user_repo.get_by_email(data.email)
        if user is None:
            return  # silent — do not leak whether the email exists

        reset_tok = generate_secure_token()
        await self._reset_repo.create(
            user_id=user.id,
            token=reset_tok,
            expires_at=datetime.now(timezone.utc) + _PASSWORD_RESET_TTL,
        )
        logger.info(
            "Password reset link for %s → POST /api/v1/auth/reset-password (token=%s)",
            user.email,
            reset_tok,
        )

    async def reset_password(self, data: ResetPasswordRequest) -> None:
        """Consume a password-reset token and update the user's hashed password."""
        entry = await self._reset_repo.get_by_token(data.token)

        if entry is None or entry.used_at is not None:
            raise UnauthorizedException("Invalid or already-used password reset link")

        expires = entry.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if expires < datetime.now(timezone.utc):
            raise UnauthorizedException("Password reset link has expired — request a new one")

        user = await self._user_repo.get_by_id(entry.user_id)
        if user is None:
            raise UnauthorizedException("User not found")

        await self._user_repo.update(user, hashed_password=hash_password(data.new_password))
        await self._reset_repo.mark_used(entry)

    # ── Change password ───────────────────────────────────────────────────────

    async def change_password(self, user_id: UUID, data: PasswordChange) -> None:
        """Verify the current password then store the new hash."""
        user = await self._user_repo.get_by_id(user_id)
        if user is None:
            raise UnauthorizedException("User not found")

        if not verify_password(data.current_password, user.hashed_password):
            raise UnauthorizedException("Current password is incorrect")

        if data.current_password == data.new_password:
            raise ConflictException("New password must differ from the current password")

        await self._user_repo.update(user, hashed_password=hash_password(data.new_password))
