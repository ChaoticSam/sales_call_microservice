from logging.config import fileConfig
import asyncio
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
import os
import sys

# Add app directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.db import Base  # Import Base
from app.models import *  # Import all models to register them
from app.db import get_database_url  # Function we'll write next

# Alembic Config
config = context.config
fileConfig(config.config_file_name)

# Use env var DB_URL
config.set_main_option("sqlalchemy.url", get_database_url(sync=True))  # We'll define this

target_metadata = Base.metadata

def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def run_migrations():
        async with connectable.connect() as connection:
            await connection.run_sync(
                lambda conn: context.configure(
                    connection=conn,
                    target_metadata=target_metadata,
                    compare_type=True
                )
            )
            with context.begin_transaction():
                context.run_migrations()

    asyncio.run(run_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
