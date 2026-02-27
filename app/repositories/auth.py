import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth import EmailVerificationToken, PasswordResetToken, RevokedToken


class RevokedTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def revoke(
        self,
        jti: str,
        user_id: uuid.UUID,
        token_type: str,
        expires_at: datetime,
    ) -> RevokedToken:
        """Add a jti to the blacklist."""
        entry = RevokedToken(
            jti=jti,
            user_id=user_id,
            token_type=token_type,
            expires_at=expires_at,
        )
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def is_revoked(self, jti: str) -> bool:
        """Return True if the jti is present in the blacklist."""
        result = await self._session.execute(
            select(RevokedToken.id).where(RevokedToken.jti == jti).limit(1)
        )
        return result.scalar() is not None

    async def purge_expired(self) -> int:
        """Delete blacklist entries whose original token has already expired.

        Safe to call periodically — expired tokens can never be used regardless,
        so keeping them only wastes space.
        """
        result = await self._session.execute(
            delete(RevokedToken).where(
                RevokedToken.expires_at < datetime.now(timezone.utc)
            )
        )
        return result.rowcount  # type: ignore[return-value]


class VerificationTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: uuid.UUID,
        token: str,
        expires_at: datetime,
    ) -> EmailVerificationToken:
        """Replace any existing pending token for this user, then create a new one."""
        await self._session.execute(
            delete(EmailVerificationToken).where(
                EmailVerificationToken.user_id == user_id
            )
        )
        entry = EmailVerificationToken(user_id=user_id, token=token, expires_at=expires_at)
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get_by_token(self, token: str) -> EmailVerificationToken | None:
        result = await self._session.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token == token)
        )
        return result.scalar_one_or_none()

    async def delete(self, entry: EmailVerificationToken) -> None:
        await self._session.delete(entry)
        await self._session.flush()


class PasswordResetTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: uuid.UUID,
        token: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        """Invalidate any previous unused reset tokens, then create a new one."""
        await self._session.execute(
            delete(PasswordResetToken).where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used_at.is_(None),
            )
        )
        entry = PasswordResetToken(user_id=user_id, token=token, expires_at=expires_at)
        self._session.add(entry)
        await self._session.flush()
        return entry

    async def get_by_token(self, token: str) -> PasswordResetToken | None:
        result = await self._session.execute(
            select(PasswordResetToken).where(PasswordResetToken.token == token)
        )
        return result.scalar_one_or_none()

    async def mark_used(self, entry: PasswordResetToken) -> None:
        entry.used_at = datetime.now(timezone.utc)
        await self._session.flush()
