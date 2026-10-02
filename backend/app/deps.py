import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db, set_context
from app.models import AppUser, Membership, Tenant
from app.security import decode_token
from domain.permissions import Permission, Role, has_permission

bearer = HTTPBearer(auto_error=False)


@dataclass
class Ctx:
    db: Session
    user: AppUser
    tenant_id: uuid.UUID
    role: Role
    ip: str | None


def get_ctx(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> Ctx:
    unauthorized = HTTPException(status_code=401, detail="Autenticazione richiesta")
    if creds is None:
        raise unauthorized
    claims = decode_token(creds.credentials)
    if claims is None:
        raise unauthorized
    try:
        user_id = uuid.UUID(claims["sub"])
        tenant_id = uuid.UUID(claims["tid"])
    except (KeyError, ValueError):
        raise unauthorized from None

    set_context(db, tenant_id=tenant_id, user_id=user_id)
    user = db.get(AppUser, user_id)
    if user is None or not user.active:
        raise unauthorized
    membership = db.scalar(
        select(Membership).where(Membership.user_id == user_id, Membership.tenant_id == tenant_id)
    )
    tenant = db.get(Tenant, tenant_id)
    if membership is None or tenant is None or not tenant.active:
        raise HTTPException(status_code=403, detail="Nessun accesso a questa azienda")
    return Ctx(
        db=db,
        user=user,
        tenant_id=tenant_id,
        role=Role(membership.role),
        ip=request.client.host if request.client else None,
    )


def require(permission: Permission):
    def checker(ctx: Ctx = Depends(get_ctx)) -> Ctx:
        if not has_permission(ctx.role, permission):
            raise HTTPException(status_code=403, detail="Permesso negato")
        return ctx

    return checker
