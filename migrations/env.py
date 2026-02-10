"""
Alembic Environment Configuration

Handles database connection and migration context.
"""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import models for autogenerate support
from src.brain.db.models import Base

# Alembic Config object
config = context.config

# Setup logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for autogenerate
target_metadata = Base.metadata


def get_url():
    """Get database URL from environment or config."""
    return os.getenv(
        "DATABASE_URL",
        config.get_main_option("sqlalchemy.url"),
    )


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    Generates SQL script without connecting to database.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    Creates connection and runs migrations.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
