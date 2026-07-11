"""
PAC Backend — Database Engine & Session Factory

Async SQLAlchemy engine for FastAPI runtime.
Sync engine is configured in alembic/env.py for migrations only.
"""

import logging
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

logger = logging.getLogger(__name__)

# ── Async engine (FastAPI runtime) ────────────────────────
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,      # Reconnect on stale connections
    pool_recycle=3600,       # Recycle connections every hour
)

# ── Session factory ────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Allow attribute access after commit
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    """
    Declarative base for all SQLAlchemy ORM models.
    Alembic autogenerate reads metadata from this base.
    """
    pass


async def get_db_session() -> AsyncSession:  # type: ignore[return]
    """
    FastAPI dependency: yields an AsyncSession with automatic
    commit on success and rollback on exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
