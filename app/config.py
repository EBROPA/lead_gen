"""Application configuration management."""

import secrets
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

    # ===========================================
    # AI Providers (all FREE options)
    # ===========================================

    # Google Gemini (RECOMMENDED - 60 req/min free)
    # Get key: https://aistudio.google.com/app/apikey
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-1.5-flash"

    # Groq (VERY FAST - generous free tier)
    # Get key: https://console.groq.com/keys
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.1-8b-instant"

    # OpenRouter (many free models)
    # Get key: https://openrouter.ai/keys
    openrouter_api_key: Optional[str] = None
    openrouter_model: str = "mistralai/mistral-7b-instruct:free"

    # Ollama (LOCAL - completely free, no API key needed)
    # Install: https://ollama.ai
    # Then run: ollama pull llama3.2
    ollama_enabled: bool = False
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2"

    # ===========================================
    # Application Settings
    # ===========================================

    app_name: str = "Lead Generation System"
    debug: bool = True

    # SECRET_KEY - используется для подписи сессий и токенов
    # Генерируется автоматически, но лучше задать свой в .env
    # Можно сгенерировать командой: python -c "import secrets; print(secrets.token_hex(32))"
    secret_key: str = secrets.token_hex(32)

    # Search Settings
    search_interval_minutes: int = 60
    max_leads_per_search: int = 50

    # ===========================================
    # Telegram (optional - for advanced parsing)
    # ===========================================
    # Получить: https://my.telegram.org/apps
    telegram_api_id: Optional[str] = None
    telegram_api_hash: Optional[str] = None
    telegram_phone: Optional[str] = None

    # ===========================================
    # Email Settings (optional - for sending proposals)
    # ===========================================
    # Примеры бесплатных SMTP:
    # - Gmail: smtp.gmail.com:587 (нужен App Password)
    # - Yandex: smtp.yandex.ru:587
    # - Mail.ru: smtp.mail.ru:587
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    email_from: Optional[str] = None

    # Redis (optional, for background tasks)
    redis_url: Optional[str] = None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
