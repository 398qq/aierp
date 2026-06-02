"""Alembic environment — pulls DB URL from app.config.settings and uses app's Base.metadata."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import app modules to register models with Base.metadata
from app.config import settings
from app.database import Base
import app.models.user  # noqa: F401
import app.models.rbac  # noqa: F401
import app.models.customer  # noqa: F401
import app.models.product  # noqa: F401
import app.models.sales  # noqa: F401
import app.models.transaction  # noqa: F401
import app.models.finance  # noqa: F401
import app.models.account  # noqa: F401
import app.models.approval  # noqa: F401
import app.models.report  # noqa: F401
import app.models.document  # noqa: F401

# Alembic Config
config = context.config

# Override DB URL from app settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Configure logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emits SQL without DB session)."""
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


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode (with DB connection)."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
