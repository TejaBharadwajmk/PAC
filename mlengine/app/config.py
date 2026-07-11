"""
PAC — ML Engine Settings

Loads configuration from environment variables / .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class MLSettings(BaseSettings):
    # Model configuration
    MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIM: int = 384
    MAX_BATCH_SIZE: int = 500

    # Service info
    SERVICE_HOST: str = "0.0.0.0"
    SERVICE_PORT: int = 5001

    # PostgreSQL — for writing embeddings directly (optional bulk mode)
    DATABASE_URL: str = "postgresql+asyncpg://pac_user:pac_password@postgres:5432/pac_db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = MLSettings()
