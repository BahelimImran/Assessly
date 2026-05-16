from logging.config import fileConfig

from alembic import context

from app.core.config import DATABASE_URL
from app.db.postgres import Base

# noqa: F401 - Ignore lint warning: imported but unused
# This import is important even though it looks unused.

# Why: SQLAlchemy only knows about models after Python imports them.

# Without this, Alembic may not see:

# users
# documents
# upload_sessions
# ingestion_jobs
# audit_events

from app.models import metadata_models  

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


# Runs migrations without creating a live DB connection.
# It generates SQL using the URL only.
# Less commonly used.
def run_migrations_offline():
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# This is the normal path.

# It:
# Creates SQLAlchemy engine.
# Connects to Postgres.
# Configures Alembic with that connection.
# Runs migrations inside a transaction.

def run_migrations_online():
    from sqlalchemy import create_engine

    connectable = create_engine(DATABASE_URL, pool_pre_ping=True)

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
