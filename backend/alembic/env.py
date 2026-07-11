"""
PAC — Alembic Migration Environment

Uses synchronous psycopg2 engine (DATABASE_URL_SYNC) because Alembic does not
natively support async engines in standard migration runs.
"""

import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

load_dotenv()

# Alembic Config object from alembic.ini
config = context.config

# Logging setup
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Import ALL models so Alembic sees every table ──────────
from app.database import Base  # noqa: E402
import app.models.user          # noqa: E402, F401
import app.models.crime         # noqa: E402, F401
import app.models.criminal      # noqa: E402, F401
import app.models.victim        # noqa: E402, F401
import app.models.crime_dna     # noqa: E402, F401
import app.models.behaviour     # noqa: E402, F401

target_metadata = Base.metadata

# Override DB URL from environment (takes precedence over alembic.ini)
sync_url = os.getenv("DATABASE_URL_SYNC")
if sync_url:
    config.set_main_option("sqlalchemy.url", sync_url)


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL script)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations with a live DB connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
