"""Application configuration loaded from environment variables and optional runtime config."""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime settings for ResumeCraft backend."""

    APP_NAME: str = "ResumeCraft API"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database: SQLite for local dev, PostgreSQL in Docker/production
    DATABASE_URL: str = f"sqlite:///{(BASE_DIR / 'resumecraft_dev.db').as_posix()}"

    # Redis (optional in local dev, used in Docker/production)
    REDIS_URL: Optional[str] = None

    # S3 / MinIO (optional in local dev; falls back to local_storage/)
    S3_ENDPOINT_URL: Optional[str] = None
    S3_ACCESS_KEY: Optional[str] = None
    S3_SECRET_KEY: Optional[str] = None
    S3_BUCKET_NAME: str = "resumecraft-exports"
    S3_REGION: str = "us-east-1"
    LOCAL_STORAGE_DIR: str = str(BASE_DIR / "local_storage")

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    LOGIN_RATE_LIMIT_MAX_ATTEMPTS: int = 10
    LOGIN_RATE_LIMIT_WINDOW_SECONDS: int = 300

    # Frontend & OAuth
    FRONTEND_URL: str = "http://localhost:3000"
    BACKEND_URL: str = "http://localhost:8000"
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None

    # AI settings
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    AI_DAILY_LIMIT: int = 10
    AI_MOCK_MODE: bool = True
    AI_TIMEOUT_SECONDS: float = 20.0

    # Limits from ТЗ
    MAX_WORK_EXPERIENCES: int = 15
    MAX_SKILLS: int = 30

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()


def get_ai_daily_limit() -> int:
    """Read AI daily limit dynamically from runtime config or env without redeploy.

    Allows changing the daily limit via `ai_runtime_config.json` or `AI_DAILY_LIMIT`
    without restarting or releasing a new build.
    """
    runtime_cfg_path = BASE_DIR / "ai_runtime_config.json"
    if runtime_cfg_path.exists():
        try:
            data = json.loads(runtime_cfg_path.read_text(encoding="utf-8"))
            if isinstance(data.get("ai_daily_limit"), int) and data["ai_daily_limit"] >= 0:
                return data["ai_daily_limit"]
        except (OSError, ValueError, TypeError):
            pass

    env_val = os.getenv("AI_DAILY_LIMIT")
    if env_val is not None:
        try:
            parsed = int(env_val)
            if parsed >= 0:
                return parsed
        except ValueError:
            pass

    return get_settings().AI_DAILY_LIMIT
