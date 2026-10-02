import pyotp

from app import security
from app.config import settings
from tests.api.conftest import API, PASSWORD


def test_login_ok_e_me(client, make_account):
    acc = make_account("ADMIN")
    r = client.get(f"{API}/auth/me", headers=acc.headers)
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == acc.email
    assert body["role"] == "ADMIN"
    assert "users:manage" in body["permissions"]


def test_login_password_errata(client, make_account):
    acc = make_account("ADMIN")
    r = client.post(f"{API}/auth/login", json={"email": acc.email, "password": "sbagliata-123"})
    assert r.status_code == 401


def test_senza_token_401_e_token_falso_401(client):
    assert client.get(f"{API}/sites").status_code == 401
    r = client.get(f"{API}/sites", headers={"Authorization": "Bearer abc.def.ghi"})
    assert r.status_code == 401


def test_blocco_dopo_troppi_tentativi(client, make_account, monkeypatch):
    monkeypatch.setattr(settings, "login_max_failures", 3)
    acc = make_account("ADMIN")
    for _ in range(3):
        client.post(f"{API}/auth/login", json={"email": acc.email, "password": "x" * 12})
    r = client.post(f"{API}/auth/login", json={"email": acc.email, "password": PASSWORD})
    assert r.status_code == 429
    security.reset_login_failures(f"{acc.email}|testclient")


def test_totp_flusso_completo(client, make_account):
    acc = make_account("ADMIN")
    setup = client.post(f"{API}/auth/totp/setup", headers=acc.headers).json()
    code = pyotp.TOTP(setup["secret"]).now()
    assert client.post(
        f"{API}/auth/totp/enable", json={"code": code}, headers=acc.headers
    ).status_code == 204

    r = client.post(f"{API}/auth/login", json={"email": acc.email, "password": PASSWORD})
    assert r.status_code == 401 and r.json()["detail"] == "totp_required"

    r = client.post(
        f"{API}/auth/login",
        json={"email": acc.email, "password": PASSWORD, "totp_code": pyotp.TOTP(setup["secret"]).now()},
    )
    assert r.status_code == 200


def test_utente_in_due_aziende_cambia_tenant(client, make_account):
    first = make_account("ADMIN")
    second = make_account("ADMIN")
    from app import provisioning

    provisioning.add_membership(first.user_id, second.tenant_id, "AUDITOR")
    r = client.post(
        f"{API}/auth/switch-tenant",
        json={"tenant_id": str(second.tenant_id)},
        headers=first.headers,
    )
    assert r.status_code == 200
    assert r.json()["role"] == "AUDITOR"
    token = r.json()["access_token"]
    me = client.get(f"{API}/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["tenant_id"] == str(second.tenant_id)


def test_switch_verso_azienda_non_propria_403(client, make_account):
    a = make_account("ADMIN")
    b = make_account("ADMIN")
    r = client.post(
        f"{API}/auth/switch-tenant", json={"tenant_id": str(b.tenant_id)}, headers=a.headers
    )
    assert r.status_code == 403


def test_admin_gestisce_utenti_operatore_no(client, make_account):
    admin = make_account("ADMIN")
    r = client.post(
        f"{API}/users",
        json={
            "email": "nuovo.operatore@example.test",
            "full_name": "Nuovo Operatore",
            "password": "una-password-lunga-1",
            "role": "OPERATORE",
        },
        headers=admin.headers,
    )
    assert r.status_code == 201, r.text
    assert any(u["email"] == "nuovo.operatore@example.test" for u in client.get(
        f"{API}/users", headers=admin.headers).json())

    operatore = make_account("OPERATORE", admin.tenant_id)
    assert client.get(f"{API}/users", headers=operatore.headers).status_code == 403


def test_non_si_puo_rimuovere_l_ultimo_admin(client, make_account):
    admin = make_account("ADMIN")
    users = client.get(f"{API}/users", headers=admin.headers).json()
    me = next(u for u in users if u["email"] == admin.email)
    assert client.delete(f"{API}/users/{me['membership_id']}", headers=admin.headers).status_code == 409
    r = client.patch(
        f"{API}/users/{me['membership_id']}", json={"role": "OPERATORE"}, headers=admin.headers
    )
    assert r.status_code == 409


def test_cambio_password(client, make_account):
    acc = make_account("ADMIN")
    r = client.post(
        f"{API}/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "nuova-password-456"},
        headers=acc.headers,
    )
    assert r.status_code == 204
    r = client.post(
        f"{API}/auth/login", json={"email": acc.email, "password": "nuova-password-456"}
    )
    assert r.status_code == 200
