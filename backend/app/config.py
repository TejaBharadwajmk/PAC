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

    # ── Redis & Task Queue ──────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    CELERY_ENABLED: bool = True

    # ── ML Engine ──────────────────────────────────────────
    MLENGINE_URL: str = "http://mlengine:5001"

    # ── Ollama (AI Assistant only) ─────────────────────────
    OLLAMA_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "mistral"
    OLLAMA_TIMEOUT: float = 60.0

    # ── AI Investigation Assistant (Phase 4.1) ─────────────
    # Provider: 'gemini' | 'ollama' | 'mock'
    LLM_PROVIDER: str = "gemini"
    # Gemini model name (google-generativeai)
    LLM_MODEL_NAME: str = "gemini-1.5-flash"
    # Gemini API key (required when LLM_PROVIDER=gemini)
    GEMINI_API_KEY: str = ""
    # Max ranked evidence items passed to the LLM context
    EVIDENCE_RANKER_TOP_N: int = 10

    # ── Hybrid Retrieval Ranking Weights (Phase 1-3) ──────
    HYBRID_SEMANTIC_WEIGHT: float = 0.50
    HYBRID_FTS_WEIGHT: float = 0.30
    HYBRID_MO_WEIGHT: float = 0.20

    # ── MO Feature-Specific Similarity Weights ────────────
    MO_CRIME_TYPE_WEIGHT: float = 0.15
    MO_CRIME_METHOD_WEIGHT: float = 0.15
    MO_WEAPON_WEIGHT: float = 0.15
    MO_ENTRY_METHOD_WEIGHT: float = 0.12
    MO_TARGET_WEIGHT: float = 0.12
    MO_ESCAPE_WEIGHT: float = 0.08
    MO_TIME_WEIGHT: float = 0.08
    MO_GANG_WEIGHT: float = 0.08
    MO_DISTRICT_WEIGHT: float = 0.07

    # ── CORS ───────────────────────────────────────────────
    CORS_ORIGINS: List[str] = []

    @property
    def async_database_url(self) -> str:
        """Ensures asyncpg driver prefix for runtime SQLAlchemy engine."""
        url = self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def sync_database_url(self) -> str:
        """Ensures psycopg2 driver prefix for Alembic migrations."""
        url = self.DATABASE_URL_SYNC or self.DATABASE_URL
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+psycopg2://"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        elif url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        return url

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

