"""Schema iniziale F1: tabelle, ruolo applicativo, RLS, immutabilita audit.

Le tabelle sono create dai modelli (create_all) solo per questa migrazione iniziale;
dalle migrazioni successive in poi si scrivono operazioni esplicite.

NB: nessun carattere percento nelle istruzioni SQL (driver psycopg, nessun parametro).

Revision ID: 0001
Revises:
"""

from alembic import op

from app.config import settings
from app.models import Base

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

APP_ROLE = "feedtrace_app"


def upgrade() -> None:
    bind = op.get_bind()

    def run(sql: str) -> None:
        bind.exec_driver_sql(sql)

    Base.metadata.create_all(bind=bind)

    # Ruolo applicativo: NON proprietario, senza BYPASSRLS -> soggetto alle policy.
    password = settings.app_db_password.replace("'", "''")
    run(
        "DO $do$ BEGIN "
        f"IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{APP_ROLE}') THEN "
        f"CREATE ROLE {APP_ROLE} LOGIN PASSWORD '{password}' NOSUPERUSER NOBYPASSRLS; "
        "END IF; END $do$"
    )
    run(f"GRANT USAGE ON SCHEMA public TO {APP_ROLE}")

    run(
        "CREATE FUNCTION app_current_tenant() RETURNS uuid LANGUAGE sql STABLE AS "
        "$$ SELECT NULLIF(current_setting('app.tenant_id', true), '')::uuid $$"
    )
    run(
        "CREATE FUNCTION app_current_user() RETURNS uuid LANGUAGE sql STABLE AS "
        "$$ SELECT NULLIF(current_setting('app.user_id', true), '')::uuid $$"
    )

    # RLS: ogni tabella con tenant_id e' visibile/scrivibile solo per il tenant corrente.
    special = {"membership"}
    for table in Base.metadata.sorted_tables:
        if "tenant_id" not in table.c or table.name in special:
            continue
        run(f"ALTER TABLE {table.name} ENABLE ROW LEVEL SECURITY")
        run(f"ALTER TABLE {table.name} FORCE ROW LEVEL SECURITY")
        run(
            f"CREATE POLICY tenant_isolation ON {table.name} "
            "USING (tenant_id = app_current_tenant()) "
            "WITH CHECK (tenant_id = app_current_tenant())"
        )

    # Membership: visibile per il tenant corrente o per l'utente corrente (login, cambio tenant).
    run("ALTER TABLE membership ENABLE ROW LEVEL SECURITY")
    run("ALTER TABLE membership FORCE ROW LEVEL SECURITY")
    run(
        "CREATE POLICY membership_access ON membership "
        "USING (tenant_id = app_current_tenant() OR user_id = app_current_user()) "
        "WITH CHECK (tenant_id = app_current_tenant())"
    )

    # Tenant: leggibile solo se corrente o se l'utente ne e' membro. Nessuna scrittura da app.
    run("ALTER TABLE tenant ENABLE ROW LEVEL SECURITY")
    run("ALTER TABLE tenant FORCE ROW LEVEL SECURITY")
    run(
        "CREATE POLICY tenant_visible ON tenant FOR SELECT "
        "USING (id = app_current_tenant() OR id IN "
        "(SELECT tenant_id FROM membership WHERE user_id = app_current_user()))"
    )

    # Privilegi minimi per il ruolo applicativo.
    run(f"GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO {APP_ROLE}")
    run(f"GRANT DELETE ON membership, container_allowed_material TO {APP_ROLE}")
    run(f"REVOKE UPDATE ON audit_log FROM {APP_ROLE}")
    run(f"REVOKE INSERT, UPDATE ON tenant FROM {APP_ROLE}")

    # Audit log immutabile anche per il proprietario (RF-14).
    run(
        "CREATE FUNCTION prevent_mutation() RETURNS trigger LANGUAGE plpgsql AS "
        "$$ BEGIN RAISE EXCEPTION 'Tabella immutabile: modifica non consentita'; END $$"
    )
    run(
        "CREATE TRIGGER audit_log_immutable BEFORE UPDATE OR DELETE ON audit_log "
        "FOR EACH ROW EXECUTE FUNCTION prevent_mutation()"
    )


def downgrade() -> None:
    raise NotImplementedError("Downgrade della migrazione iniziale non supportato")
