"""Creazione di tenant e utenti con il ruolo amministrativo (CLI e test).

Fuori dall'API per scelta (ADR D17): il super admin opera solo da riga di comando.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import admin_engine
from app.models import AppUser, Membership, Tenant
from app.security import hash_password
from domain.permissions import Role


def create_tenant(name: str, vat_number: str | None = None) -> uuid.UUID:
    with Session(admin_engine) as db:
        tenant = Tenant(name=name, vat_number=vat_number)
        db.add(tenant)
        db.commit()
        return tenant.id


def create_user(
    email: str, password: str, full_name: str, *, superadmin: bool = False
) -> uuid.UUID:
    with Session(admin_engine) as db:
        user = AppUser(
            email=email.strip().lower(),
            password_hash=hash_password(password),
            full_name=full_name,
            is_superadmin=superadmin,
        )
        db.add(user)
        db.commit()
        return user.id


def add_membership(user_id: uuid.UUID, tenant_id: uuid.UUID, role: Role | str) -> None:
    with Session(admin_engine) as db:
        db.add(Membership(user_id=user_id, tenant_id=tenant_id, role=Role(role).value))
        db.commit()


def find_user_id(email: str) -> uuid.UUID | None:
    with Session(admin_engine) as db:
        return db.scalar(select(AppUser.id).where(AppUser.email == email.strip().lower()))
