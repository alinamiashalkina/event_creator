import asyncio
import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from db.models import Base

config = context.config

fileConfig(config.config_file_name)

load_dotenv()

DATABASE_URL = "postgresql+asyncpg://{}:{}@{}:{}/{}".format(
    os.environ["DB_USER"],
    os.environ["DB_PASSWORD"],
    os.environ["DB_HOST"],
    os.environ["DB_PORT"],
    os.environ["DB_NAME"]
)

config.set_main_option("sqlalchemy.url", DATABASE_URL)


connectable = create_async_engine(config.get_main_option("sqlalchemy.url"),
                                  poolclass=pool.AsyncAdaptedQueuePool)


def run_migrations_offline():
    context.configure(
        url=DATABASE_URL, target_metadata=Base.metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online():
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
