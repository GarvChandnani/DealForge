"""
Alembic environment configuration for DealForge.

Reads DATABASE_URL from environment / .env and uses the synchronous
driver variant for migrations (psycopg2 or sqlite, not async drivers).
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.engine import make_url

# ── Path setup: allow importing backend models ────────────────────────────────
# Assumes `alembic upgrade head` is run from the repo root.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BACKEND_DIR = os.path.join(REPO_ROOT, "backend")
for p in [REPO_ROOT, BACKEND_DIR]:
    if p not in sys.path:
        sys.path.insert(0, p)

from dotenv import load_dotenv
load_dotenv(os.path.join(BACKEND_DIR, ".env"))
load_dotenv(os.path.join(REPO_ROOT, ".env"))

# ── Import models so Alembic can see the metadata ────────────────────────────
from app.models.base import Base  # noqa: F401
import app.models.deal  # noqa: F401
import app.models.contact  # noqa: F401
import app.models.mandate_generation  # noqa: F401

# ── Alembic config ────────────────────────────────────────────────────────────
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Override sqlalchemy.url from env, using sync driver
_raw_url = os.getenv("DATABASE_URL", "sqlite:///./dealforge.db")
# Render provides bare postgres:// — rewrite to postgresql+psycopg2://
if _raw_url.startswith("postgres://"):
    _raw_url = "postgresql+psycopg2://" + _raw_url[len("postgres://"):]
_sync_url = (
    _raw_url
    .replace("sqlite+aiosqlite", "sqlite")
    .replace("postgresql+asyncpg", "postgresql+psycopg2")
    .replace("postgresql://", "postgresql+psycopg2://")
)
database_url = make_url(_sync_url)
if (
    database_url.get_backend_name() == "sqlite"
    and database_url.database not in (None, ":memory:")
    and not os.path.isabs(database_url.database)
):
    database_url = database_url.set(
        database=os.path.abspath(os.path.join(BACKEND_DIR, database_url.database))
    )
config.set_main_option(
    "sqlalchemy.url",
    database_url.render_as_string(hide_password=False),
)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL script)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (apply directly to DB)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
