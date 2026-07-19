from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Uses pydantic-settings for automatic .env file loading and type validation.
    All values can be overridden via environment variables (12-factor app).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "FiscalMind"
    APP_ENV: Literal["development", "production", "testing"] = "development"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # ── Security ──────────────────────────────────────────────────────────────
    SECRET_KEY: str = Field(..., min_length=32)
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    BACKEND_CORS_ORIGINS: list[AnyHttpUrl | str] = [
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list) -> list:
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://fiscalmind:fiscalmind_secret@localhost:5432/fiscalmind_db"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Qdrant ────────────────────────────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_URL: str | None = None  # Full HTTPS URL for Qdrant Cloud
    QDRANT_API_KEY: str | None = None

    # ── OCR ───────────────────────────────────────────────────────────────────
    OCR_SERVICE_URL: str = "http://localhost:8002"

    # ── Voyage AI ─────────────────────────────────────────────────────────────
    VOYAGE_API_KEY: str = Field(default="")
    VOYAGE_EMBEDDING_MODEL: str = "voyage-multilingual-2"
    VOYAGE_RERANK_MODEL: str = "rerank-2.5"

    # ── LLM / Groq ────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = Field(default="")
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    LLM_MAX_TOKENS: int = 4096
    LLM_TEMPERATURE: float = 0.1  # Low for deterministic financial analysis

    # ── Storage ───────────────────────────────────────────────────────────────
    STORAGE_BACKEND: Literal["local", "s3"] = "local"
    UPLOAD_DIR: str = "/app/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── AWS S3 (optional) ─────────────────────────────────────────────────────
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None
    AWS_S3_BUCKET: str | None = None
    AWS_S3_REGION: str = "ap-southeast-1"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    """
    Returns a cached singleton of Settings.
    Using lru_cache ensures the .env file is only read once at startup.
    """
    return Settings()


# Module-level alias for convenient imports: `from app.core.config import settings`
settings: Settings = get_settings()
