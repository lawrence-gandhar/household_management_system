import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, NamedTuple

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Password helpers ─────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_context.verify(plain, hashed)


# ── Secure random token ───────────────────────────────────────────────────────

def generate_secure_token(nbytes: int = 48) -> str:
    """Return a URL-safe, cryptographically secure random string.

    Default ``nbytes=48`` produces a ~64-character token with 384 bits of
    entropy — suitable for email-verification and password-reset links.
    """
    return secrets.token_urlsafe(nbytes)


# ── JWT token helpers ─────────────────────────────────────────────────────────

class CreatedToken(NamedTuple):
    """Return value from :func:`create_access_token` / :func:`create_refresh_token`."""

    token: str            # encoded JWT string to send to the client
    jti: str              # JWT ID claim (UUID string) — store for revocation tracking
    expires_at: datetime  # UTC datetime when this token expires


def _build_token(subject: Any, token_type: str, expires_delta: timedelta) -> CreatedToken:
    jti = str(uuid.uuid4())
    expire = datetime.now(timezone.utc) + expires_delta
    payload = {
        "sub": str(subject),
        "exp": expire,
        "type": token_type,
        "jti": jti,
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return CreatedToken(token=token, jti=jti, expires_at=expire)


def create_access_token(subject: Any) -> CreatedToken:
    return _build_token(
        subject,
        "access",
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(subject: Any) -> CreatedToken:
    return _build_token(
        subject,
        "refresh",
        timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str) -> dict:
    """Decode and verify a JWT.  Raises :class:`~jose.JWTError` on failure."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
