"""
PAC Backend — Application Settings

Uses pydantic-settings to load configuration from environment variables / .env file.
All settings have sensible defaults for development; override in production via env vars.
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # ── Application ────────────────────────────────────────
    APP_NAME: str = "PAC - PoliceIT Analytics Core"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # ── PostgreSQL ─────────────────────────────────────────
    # asyncpg for runtime; psycopg2 for Alembic migrations
    DATABASE_URL: str = "postgresql+asyncpg://pac_user:pac_password@postgres:5432/pac_db"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://pac_user:pac_password@postgres:5432/pac_db"

    # ── JWT Security ───────────────────────────────────────
    SECRET_KEY: str = "change-this-in-production-to-a-strong-random-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── Neo4j ──────────────────────────────────────────────
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USERNAME: str = "neo4j"
    NEO4J_PASSWORD: str = "pac_neo4j_password_2024"

    # ── Redis ──────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"

    # ── ML Engine ──────────────────────────────────────────
    MLENGINE_URL: str = "http://mlengine:5001"

    # ── Ollama (AI Assistant only) ─────────────────────────
    OLLAMA_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "mistral"

    # ── CORS ───────────────────────────────────────────────
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://frontend:3000"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance — loaded once, reused across the app lifecycle."""
    return Settings()


# Global singleton for import convenience
settings = get_settings()
