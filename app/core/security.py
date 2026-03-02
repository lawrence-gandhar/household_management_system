import base64
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, NamedTuple

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings


# ── Password helpers ─────────────────────────────────────────────────────────
#
# passlib 1.7.4 is incompatible with bcrypt ≥ 4.0 (its detect_wrap_bug helper
# passes a >72-byte test string which the newer bcrypt library rejects with
# ValueError).  We call bcrypt directly to avoid the issue.
#
# SHA-256 pre-hashing ensures bcrypt never sees a raw password, sidestepping
# the 72-byte truncation limit entirely.  Both helpers MUST apply _prehash so
# that hash and verify are symmetric.

def _prehash(plain: str) -> bytes:
    """Return the base64-encoded SHA-256 digest of *plain* as bytes (44 chars)."""
    digest = hashlib.sha256(plain.encode("utf-8")).digest()
    return base64.b64encode(digest)


def hash_password(plain: str) -> str:
    return bcrypt.hashpw(_prehash(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prehash(plain), hashed.encode("utf-8"))
    except Exception:
        return False


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
