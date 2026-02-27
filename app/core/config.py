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

    # AI Integration (optional)
    AI_SERVICE_URL: str = ""
    AI_SERVICE_API_KEY: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
