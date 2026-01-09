"""Application configuration management."""

from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "sqlite+aiosqlite:///./lead_gen.db"

    # OpenAI
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"

    # Application
    app_name: str = "Lead Generation System"
    debug: bool = True
    secret_key: str = "change-me-in-production"

    # Search Settings
    search_interval_minutes: int = 60
    max_leads_per_search: int = 50

    # Telegram (optional)
    telegram_api_id: Optional[str] = None
    telegram_api_hash: Optional[str] = None
    telegram_phone: Optional[str] = None

    # Email (optional)
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None

    # Redis (optional)
    redis_url: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
