import uuid
from collections.abc import Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

# Solo per migrazioni, provisioning (CLI) e test: ruolo proprietario, aggira la RLS.
admin_engine = create_engine(settings.admin_database_url, pool_pre_ping=True)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()  # rollback implicito di ogni transazione non confermata


def set_context(
    db: Session, *, tenant_id: uuid.UUID | None = None, user_id: uuid.UUID | None = None
) -> None:
    """Imposta tenant e utente per la transazione corrente (usati dalle policy RLS).

    Valori locali alla transazione: dopo commit/rollback vanno reimpostati.
    """
    db.execute(
        text("select set_config('app.tenant_id', :t, true), set_config('app.user_id', :u, true)"),
        {"t": str(tenant_id) if tenant_id else "", "u": str(user_id) if user_id else ""},
    )
