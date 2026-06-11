"""Alembic async migration environment."""
import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

# Add src to path so app imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from app.models import Base  # noqa: E402 — must come after sys.path setup

# Import all models to register them with Base.metadata
import app.models.product  # noqa: F401
import app.models.document  # noqa: F401
import app.models.requirement  # noqa: F401
import app.models.control  # noqa: F401
import app.models.evidence  # noqa: F401
import app.models.risk  # noqa: F401
import app.models.finding  # noqa: F401
import app.models.audit  # noqa: F401
import app.models.parse_job  # noqa: F401

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    # Allow runtime DATABASE_URL override (used by entrypoint.sh in Azure)
    url = os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    connectable = create_async_engine(url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
