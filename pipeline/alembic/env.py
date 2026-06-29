import os
from alembic import context
from sqlalchemy import engine_from_config, pool

config = context.config

config.set_main_option(
    "sqlalchemy.url",
    f"postgresql+psycopg2://{os.environ['POSTGRES_USER']}"
    f":{os.environ['POSTGRES_PASSWORD']}"
    f"@{os.environ.get('POSTGRES_HOST', 'localhost')}"
    f":5432/{os.environ['POSTGRES_DB']}",
)


def run_migrations() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()


run_migrations()
