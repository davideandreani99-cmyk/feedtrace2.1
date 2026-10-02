"""Riga di comando: python -m app.cli <comando>

  create-tenant --name "Azienda" [--vat 01234567890]
  create-user --email a@b.it --password '...' --name "Nome" [--superadmin]
  add-member --email a@b.it --tenant-id <uuid> --role ADMIN
  seed-dev --email admin@example.test --password '...'   (dati fittizi per sviluppo)
"""

import argparse
import uuid

from sqlalchemy.orm import Session

from app import provisioning
from app.db import admin_engine
from app.models import AuditLog, Container, RawMaterial, Site, Supplier
from domain.permissions import Role


def _seed_dev(email: str, password: str) -> None:
    """Tenant fittizio con un sito, 2 fornitori, 3 materie prime e 1 silo. Solo dati inventati."""
    tenant_id = provisioning.create_tenant("Azienda Agricola Demo - Cascina Esempio")
    user_id = provisioning.find_user_id(email)
    if user_id is None:
        user_id = provisioning.create_user(email, password, "Amministratore Demo")
    provisioning.add_membership(user_id, tenant_id, Role.ADMIN)
    with Session(admin_engine) as db:
        site = Site(tenant_id=tenant_id, name="Allevamento Demo 1", asl_code="000XX001",
                    province="PR", dop_circuit=True)
        db.add(site)
        db.add_all(
            [
                Supplier(tenant_id=tenant_id, name="Mangimi Fittizi S.r.l.",
                         vat_number="IT00000000001", reg_183_number="IT-REG-0001"),
                Supplier(tenant_id=tenant_id, name="Cereali Esempio S.p.A.",
                         vat_number="IT00000000002", reg_183_number="IT-REG-0002"),
            ]
        )
        db.add_all(
            [
                RawMaterial(tenant_id=tenant_id, code="MAIS", name="Mais granella",
                            type="CEREALE", dry_matter_pct=86, dop_category="mais"),
                RawMaterial(tenant_id=tenant_id, code="ORZO", name="Orzo",
                            type="CEREALE", dry_matter_pct=87, dop_category="orzo"),
                RawMaterial(tenant_id=tenant_id, code="SOIA44", name="Farina estrazione soia 44",
                            type="PROTEICO", dry_matter_pct=88, requires_analysis=True),
            ]
        )
        db.flush()
        db.add(Container(tenant_id=tenant_id, site_id=site.id, code="SILO-01", type="SILO",
                         capacity=20000, consumption_policy="FIFO"))
        db.add(AuditLog(tenant_id=tenant_id, user_id=user_id, entity="seed", action="SEED_DEV"))
        db.commit()
    print(f"Tenant demo creato: {tenant_id}")
    print(f"Accedi con l'email {email}")


def main() -> None:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-tenant")
    p.add_argument("--name", required=True)
    p.add_argument("--vat")

    p = sub.add_parser("create-user")
    p.add_argument("--email", required=True)
    p.add_argument("--password", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--superadmin", action="store_true")

    p = sub.add_parser("add-member")
    p.add_argument("--email", required=True)
    p.add_argument("--tenant-id", required=True, type=uuid.UUID)
    p.add_argument("--role", required=True, choices=[r.value for r in Role])

    p = sub.add_parser("seed-dev")
    p.add_argument("--email", default="admin@example.test")
    p.add_argument("--password", default="cambiami-subito")

    args = parser.parse_args()
    if args.command == "create-tenant":
        print(provisioning.create_tenant(args.name, args.vat))
    elif args.command == "create-user":
        print(provisioning.create_user(args.email, args.password, args.name,
                                       superadmin=args.superadmin))
    elif args.command == "add-member":
        user_id = provisioning.find_user_id(args.email)
        if user_id is None:
            raise SystemExit("Utente non trovato")
        provisioning.add_membership(user_id, args.tenant_id, args.role)
        print("Associazione creata")
    elif args.command == "seed-dev":
        _seed_dev(args.email, args.password)


if __name__ == "__main__":
    main()
