import os
import sys
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import engine_from_config, pool, text

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

load_dotenv()

from app.database import Base
from app.models import *  # noqa: F401,F403 — ensure all models registered

config = context.config

# Override sqlalchemy.url from environment. MIGRATION_DATABASE_URL (Neon DIRECT/unpooled endpoint)
# wins over DATABASE_URL (pooled) so DDL never goes through pgbouncer.
db_url = os.getenv("MIGRATION_DATABASE_URL") or os.getenv("DATABASE_URL", "")
if "+asyncpg" in db_url:
    db_url = db_url.replace("+asyncpg", "")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Tables owned by app/rag (raw SQL, no ORM models): keep them out of autogenerate/`alembic check`.
_UNMANAGED = {"kb_chunks", "kb_meta", "kb_key_embeddings"}


def include_object(obj, name, type_, reflected, compare_to):  # noqa: ANN001
    if type_ == "table" and name in _UNMANAGED:
        return False
    return True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, include_object=include_object)
    with context.begin_transaction():
        context.run_migrations()


MIGRATION_LOCK_KEY = 727274  # arbitrary app-wide constant ("NAKSH")


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    # Serialise concurrent starts (Render briefly overlaps old and new instances on deploy): a
    # session-level advisory lock on a dedicated connection, held for the whole upgrade. Needs a
    # DIRECT Postgres connection (MIGRATION_DATABASE_URL); pgbouncer transaction pooling would drop it.
    lock_conn = connectable.connect()
    try:
        lock_conn.execute(text("SET statement_timeout = '180s'"))
        lock_conn.execute(text("SELECT pg_advisory_lock(:k)"), {"k": MIGRATION_LOCK_KEY})
        lock_conn.execute(text("SET statement_timeout = 0"))
        lock_conn.commit()
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata, include_object=include_object)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        try:
            lock_conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": MIGRATION_LOCK_KEY})
            lock_conn.commit()
        finally:
            lock_conn.close()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
