from alembic import context
from sqlalchemy import create_engine

from app.config import settings
from app.models import Base


def run_migrations_online() -> None:
    # Le migrazioni girano con il ruolo proprietario (amministrativo), non con quello applicativo.
    engine = create_engine(settings.admin_database_url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
