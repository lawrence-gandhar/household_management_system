from functools import lru_cache
from typing import Annotated, Any

from pydantic import AnyUrl, BeforeValidator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors(value: Any) -> list[str]:
    if isinstance(value, str):
        import json
        try:
            return json.loads(value)
        except Exception:
            return [v.strip() for v in value.split(",")]
    return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "Pantry Mate"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"

    # Database
    DATABASE_URL: str
    DATABASE_URL_ASYNC: str

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Admin Panel
    ADMIN_SECRET_KEY: str

    # Subscription Limits
    FREE_INVENTORY_LIMIT: int = 20
    FREE_RECIPE_LIMIT: int = 1

    # CORS
    CORS_ORIGINS: Annotated[list[str], BeforeValidator(_parse_cors)] = [
        "http://localhost:3000",
        "http://localhost:8080",
    ]

    # ── OpenAI ────────────────────────────────────────────────────
    OPENAI_API_KEY: str
    OPENAI_MODEL_RECIPE: str  = "gpt-4.1"
    OPENAI_MODEL_CHAT: str    = "gpt-4o"
    OPENAI_TIMEOUT_SECONDS: int = 30
    OPENAI_MAX_RETRIES: int   = 3

    # ── Tier-based daily AI request limits ────────────────────────
    AI_LIMIT_FREE_DAILY: int    = 5
    AI_LIMIT_PREMIUM_DAILY: int = 100

    # ── Circuit breaker ───────────────────────────────────────────
    CB_FAILURE_THRESHOLD: int  = 5
    CB_RECOVERY_TIMEOUT_S: int = 60

    # ── Redis ─────────────────────────────────────────────────────
    REDIS_URL: str            = "redis://localhost:6379/0"
    REDIS_AI_CACHE_TTL_S: int = 3600   # 1-hour recipe cache
    REDIS_RATE_WINDOW_S: int  = 86400  # 24-hour rolling window

    # ── Prompt hardening ──────────────────────────────────────────
    AI_MAX_INGREDIENTS: int   = 50     # hard cap before LLM
    AI_MAX_PROMPT_CHARS: int  = 8000   # reject oversized prompts


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]




settings = get_settings()
