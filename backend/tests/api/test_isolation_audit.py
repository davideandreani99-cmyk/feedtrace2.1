"""Isolamento tra aziende (CLAUDE.md: i tentativi cross-tenant devono fallire) e audit (RF-14)."""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.db import SessionLocal, admin_engine
from tests.api.conftest import API, create_site


# --- API ---------------------------------------------------------------------------
def test_lista_e_dettaglio_non_attraversano_i_tenant(client, make_account):
    a = make_account("ADMIN")
    b = make_account("ADMIN")
    r = client.post(f"{API}/suppliers", json={"name": "Fornitore di A"}, headers=a.headers)
    supplier_id = r.json()["id"]

    assert client.get(f"{API}/suppliers", headers=b.headers).json() == []
    assert client.get(f"{API}/suppliers/{supplier_id}", headers=b.headers).status_code == 404
    assert client.patch(
        f"{API}/suppliers/{supplier_id}", json={"name": "Hack"}, headers=b.headers
    ).status_code == 404
    assert client.delete(f"{API}/suppliers/{supplier_id}", headers=b.headers).status_code == 404
    # ...e per A nulla è cambiato
    assert client.get(f"{API}/suppliers/{supplier_id}", headers=a.headers).json()["name"] == (
        "Fornitore di A"
    )


def test_riferimento_a_sito_di_altro_tenant_rifiutato(client, make_account):
    a = make_account("ADMIN")
    b = make_account("ADMIN")
    site_a = create_site(client, a)
    r = client.post(
        f"{API}/containers",
        json={"site_id": site_a["id"], "code": "SILO-X", "type": "SILO"},
        headers=b.headers,
    )
    assert r.status_code == 422


def test_audit_log_non_visibile_ad_altri_tenant(client, make_account):
    a = make_account("ADMIN")
    b = make_account("ADMIN")
    client.post(f"{API}/suppliers", json={"name": "Solo A"}, headers=a.headers)
    assert client.get(f"{API}/audit-log", headers=b.headers).json() == []


# --- database (RLS) ----------------------------------------------------------------
def test_rls_database_nessun_contesto_nessuna_riga(client, make_account):
    a = make_account("ADMIN")
    client.post(f"{API}/suppliers", json={"name": "Visibile solo ad A"}, headers=a.headers)
    with SessionLocal() as db:
        assert db.execute(text("select count(*) from supplier")).scalar() == 0


def test_rls_database_altro_tenant_non_vede_e_non_scrive(client, make_account):
    a = make_account("ADMIN")
    b = make_account("ADMIN")
    client.post(f"{API}/suppliers", json={"name": "Fornitore A"}, headers=a.headers)

    with SessionLocal() as db:
        db.execute(text("select set_config('app.tenant_id', :t, true)"), {"t": str(b.tenant_id)})
        assert db.execute(text("select count(*) from supplier")).scalar() == 0

    with SessionLocal() as db:
        db.execute(text("select set_config('app.tenant_id', :t, true)"), {"t": str(b.tenant_id)})
        with pytest.raises(DBAPIError):
            db.execute(
                text("insert into supplier (id, tenant_id, name) values (:i, :t, 'Intruso')"),
                {"i": str(uuid.uuid4()), "t": str(a.tenant_id)},
            )


def test_ruolo_applicativo_non_aggira_la_rls(client):
    with SessionLocal() as db:
        row = db.execute(
            text("select rolsuper, rolbypassrls from pg_roles where rolname = current_user")
        ).one()
        assert row.rolsuper is False
        assert row.rolbypassrls is False


# --- audit (RF-14) -----------------------------------------------------------------
def test_audit_registra_creazione_modifica_disattivazione(client, make_account):
    acc = make_account("ADMIN")
    created = client.post(
        f"{API}/suppliers", json={"name": "Originale"}, headers=acc.headers
    ).json()
    client.patch(f"{API}/suppliers/{created['id']}", json={"name": "Modificato"}, headers=acc.headers)
    client.delete(f"{API}/suppliers/{created['id']}", headers=acc.headers)

    rows = client.get(
        f"{API}/audit-log", params={"entity_id": created["id"]}, headers=acc.headers
    ).json()
    by_action = {r["action"]: r for r in rows}
    assert set(by_action) == {"CREATE", "UPDATE", "DEACTIVATE"}
    assert by_action["UPDATE"]["before"]["name"] == "Originale"
    assert by_action["UPDATE"]["after"]["name"] == "Modificato"
    assert by_action["DEACTIVATE"]["after"]["active"] is False
    assert all(r["user_id"] == str(acc.user_id) for r in rows)


def test_audit_log_immutabile_per_ruolo_applicativo(client, make_account):
    acc = make_account("ADMIN")
    client.post(f"{API}/suppliers", json={"name": "X"}, headers=acc.headers)
    for statement in ("update audit_log set action = 'X'", "delete from audit_log"):
        with SessionLocal() as db:
            db.execute(
                text("select set_config('app.tenant_id', :t, true)"), {"t": str(acc.tenant_id)}
            )
            with pytest.raises(DBAPIError):
                db.execute(text(statement))


def test_audit_log_immutabile_anche_per_il_proprietario(client, make_account):
    acc = make_account("ADMIN")
    client.post(f"{API}/suppliers", json={"name": "Y"}, headers=acc.headers)
    for statement in ("update audit_log set action = 'X'", "delete from audit_log"):
        with admin_engine.connect() as conn:
            with pytest.raises(DBAPIError):
                conn.exec_driver_sql(statement)


def test_operatore_non_legge_audit_auditor_si(client, make_account):
    admin = make_account("ADMIN")
    client.post(f"{API}/suppliers", json={"name": "Z"}, headers=admin.headers)
    operatore = make_account("OPERATORE", admin.tenant_id)
    auditor = make_account("AUDITOR", admin.tenant_id)
    assert client.get(f"{API}/audit-log", headers=operatore.headers).status_code == 403
    assert client.get(f"{API}/audit-log", headers=auditor.headers).status_code == 200
