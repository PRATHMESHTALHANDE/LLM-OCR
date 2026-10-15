"""
Open Doc Intelligence (docintel) - Application Configuration
Pydantic v2 Settings with environment-variable loading, path resolution, and DB URL helpers.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """DocIntel centralized configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Environment & Network
    DOCINTEL_ENV: Literal["development", "production", "test"] = "development"
    DOCINTEL_HOST: str = "127.0.0.1"
    DOCINTEL_PORT: int = 8080
    DOCINTEL_LOG_LEVEL: str = "INFO"
    DOCINTEL_LOCAL_ONLY: bool = True

    # Database Configuration (Zero-setup local SQLite by default, Docker PostgreSQL for production)
    DOCINTEL_DATABASE_URL: str = Field(
        default="sqlite+aiosqlite:///./data/runtime/docintel.db",
        description="Async database connection string (SQLite fallback or PostgreSQL)",
    )
    DOCINTEL_DB_POOL_SIZE: int = 10
    DOCINTEL_DB_MAX_OVERFLOW: int = 20
    DOCINTEL_DB_TIMEOUT_SECONDS: float = 30.0

    # Storage & Model Cache
    DOCINTEL_DATA_DIR: Path = Field(
        default=Path("./data/runtime"),
        description="Root runtime data directory for uploaded files and artifacts",
    )
    DOCINTEL_MODEL_CACHE_DIR: Path = Field(
        default=Path("./data/models"),
        description="Local cache directory for downloaded open-source model weights",
    )
    DOCINTEL_MAX_UPLOAD_MB: int = 100
    DOCINTEL_MAX_PAGES: int = 500
    DOCINTEL_RETENTION_DAYS: int = 30

    # Concurrency Guards (Tuned for 4GB VRAM GPU + 16GB RAM)
    DOCINTEL_MAX_CONCURRENT_DOCUMENTS: int = 1
    DOCINTEL_MAX_CONCURRENT_PAGES: int = 1

    # OCR Subsystems
    DOCINTEL_OCR_PROVIDER: str = "paddle"
    DOCINTEL_ADVANCED_OCR_ENABLED: bool = True
    DOCINTEL_ADVANCED_OCR_PROVIDER: str = "florence2"

    # Optional Extensions
    DOCINTEL_VECTOR_ENABLED: bool = False
    DOCINTEL_QDRANT_URL: str = "http://127.0.0.1:6333"
    DOCINTEL_LANGFUSE_ENABLED: bool = False
    DOCINTEL_OTEL_ENABLED: bool = False
    DOCINTEL_AUDIO_VIDEO_ENABLED: bool = False

    @property
    def is_sqlite(self) -> bool:
        """Return True if configured database is SQLite."""
        return "sqlite" in self.DOCINTEL_DATABASE_URL.lower()

    @property
    def async_database_url(self) -> str:
        """Ensure the connection string uses an async driver."""
        url = self.DOCINTEL_DATABASE_URL
        if url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        if url.startswith("sqlite:///") and not url.startswith("sqlite+aiosqlite:///"):
            return url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """Convert async connection URL to a sync driver URL for Alembic migrations."""
        url = self.DOCINTEL_DATABASE_URL
        if "postgresql+asyncpg://" in url:
            return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        if "sqlite+aiosqlite:///" in url:
            return url.replace("sqlite+aiosqlite:///", "sqlite:///", 1)
        return url

    def ensure_directories(self) -> None:
        """Ensure essential runtime data and artifact directories exist."""
        self.DOCINTEL_DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.DOCINTEL_MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        (self.DOCINTEL_DATA_DIR / "documents").mkdir(parents=True, exist_ok=True)
        (self.DOCINTEL_DATA_DIR / "evaluations").mkdir(parents=True, exist_ok=True)
        (self.DOCINTEL_DATA_DIR / "tmp").mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Get cached singleton settings instance."""
    settings = Settings()
    settings.ensure_directories()
    return settings
