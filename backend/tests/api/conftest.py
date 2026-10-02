import uuid
from dataclasses import dataclass
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app import provisioning
from app.config import settings
from app.main import app

BACKEND = Path(__file__).resolve().parents[2]
PASSWORD = "password-di-prova-123"


@pytest.fixture(scope="session", autouse=True)
def migrated_db():
    """Ricrea lo schema e applica le migrazioni (richiede PostgreSQL, vedi README)."""
    engine = create_engine(settings.admin_database_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        conn.exec_driver_sql("DROP SCHEMA IF EXISTS public CASCADE")
        conn.exec_driver_sql("CREATE SCHEMA public")
        conn.exec_driver_sql("GRANT ALL ON SCHEMA public TO PUBLIC")
    engine.dispose()
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(scope="session")
def client(migrated_db):
    return TestClient(app)


@dataclass
class Account:
    email: str
    password: str
    user_id: uuid.UUID
    tenant_id: uuid.UUID
    token: str

    @property
    def headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"}


@pytest.fixture
def make_account(client):
    """Crea (se serve) un tenant e un utente con il ruolo indicato, ed effettua il login."""

    def _make(role: str = "ADMIN", tenant_id: uuid.UUID | None = None) -> Account:
        if tenant_id is None:
            tenant_id = provisioning.create_tenant(f"Azienda {uuid.uuid4().hex[:8]}")
        email = f"u{uuid.uuid4().hex[:10]}@example.test"
        user_id = provisioning.create_user(email, PASSWORD, "Utente di Prova")
        provisioning.add_membership(user_id, tenant_id, role)
        response = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": PASSWORD, "tenant_id": str(tenant_id)},
        )
        assert response.status_code == 200, response.text
        return Account(email, PASSWORD, user_id, tenant_id, response.json()["access_token"])

    return _make


API = "/api/v1"


def create_site(client, account: Account, asl_code: str | None = None) -> dict:
    response = client.post(
        f"{API}/sites",
        json={"name": "Sito di prova", "asl_code": asl_code or uuid.uuid4().hex[:8]},
        headers=account.headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def create_material(client, account: Account, code: str | None = None, **extra) -> dict:
    body = {
        "code": code or uuid.uuid4().hex[:8],
        "name": "Mais",
        "type": "CEREALE",
        **extra,
    }
    response = client.post(f"{API}/raw-materials", json=body, headers=account.headers)
    assert response.status_code == 201, response.text
    return response.json()
