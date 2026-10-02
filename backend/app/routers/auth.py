import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import security
from app.db import get_db, set_context
from app.deps import Ctx, get_ctx
from app.models import AppUser, Membership, Tenant
from domain.permissions import Permission, Role, permissions_for

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str
    totp_code: str | None = None
    tenant_id: uuid.UUID | None = None


class TenantRef(BaseModel):
    tenant_id: uuid.UUID
    name: str
    role: Role


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: uuid.UUID
    role: Role
    memberships: list[TenantRef]


class MeOut(BaseModel):
    user_id: uuid.UUID
    email: str
    full_name: str
    totp_enabled: bool
    tenant_id: uuid.UUID
    role: Role
    permissions: list[Permission]
    memberships: list[TenantRef]


def _memberships(db: Session, user_id: uuid.UUID) -> list[TenantRef]:
    rows = db.execute(
        select(Membership, Tenant)
        .join(Tenant, Tenant.id == Membership.tenant_id)
        .where(Membership.user_id == user_id, Tenant.active.is_(True))
        .order_by(Tenant.name)
    ).all()
    return [TenantRef(tenant_id=t.id, name=t.name, role=Role(m.role)) for m, t in rows]


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    throttle_key = f"{email}|{request.client.host if request.client else '-'}"
    if security.login_blocked(throttle_key):
        raise HTTPException(status_code=429, detail="Troppi tentativi: riprova più tardi")

    invalid = HTTPException(status_code=401, detail="Credenziali non valide")
    user = db.scalar(select(AppUser).where(AppUser.email == email))
    if user is None or not user.active or not security.verify_password(
        user.password_hash, payload.password
    ):
        security.register_login_failure(throttle_key)
        raise invalid
    if user.totp_enabled:
        if not payload.totp_code:
            raise HTTPException(status_code=401, detail="totp_required")
        if not security.verify_totp(user.totp_secret or "", payload.totp_code):
            security.register_login_failure(throttle_key)
            raise invalid

    set_context(db, user_id=user.id)
    memberships = _memberships(db, user.id)
    if not memberships:
        raise HTTPException(status_code=403, detail="Nessuna azienda associata all'utente")
    chosen = memberships[0]
    if payload.tenant_id is not None:
        match = [m for m in memberships if m.tenant_id == payload.tenant_id]
        if not match:
            raise HTTPException(status_code=403, detail="Nessun accesso a questa azienda")
        chosen = match[0]

    security.reset_login_failures(throttle_key)
    return TokenOut(
        access_token=security.create_token(user.id, chosen.tenant_id),
        tenant_id=chosen.tenant_id,
        role=chosen.role,
        memberships=memberships,
    )


class SwitchIn(BaseModel):
    tenant_id: uuid.UUID


@router.post("/switch-tenant", response_model=TokenOut)
def switch_tenant(payload: SwitchIn, ctx: Ctx = Depends(get_ctx)):
    memberships = _memberships(ctx.db, ctx.user.id)
    match = [m for m in memberships if m.tenant_id == payload.tenant_id]
    if not match:
        raise HTTPException(status_code=403, detail="Nessun accesso a questa azienda")
    return TokenOut(
        access_token=security.create_token(ctx.user.id, match[0].tenant_id),
        tenant_id=match[0].tenant_id,
        role=match[0].role,
        memberships=memberships,
    )


@router.get("/me", response_model=MeOut)
def me(ctx: Ctx = Depends(get_ctx)):
    return MeOut(
        user_id=ctx.user.id,
        email=ctx.user.email,
        full_name=ctx.user.full_name,
        totp_enabled=ctx.user.totp_enabled,
        tenant_id=ctx.tenant_id,
        role=ctx.role,
        permissions=sorted(permissions_for(ctx.role)),
        memberships=_memberships(ctx.db, ctx.user.id),
    )


# --- password ---------------------------------------------------------------------
class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10, max_length=200)


@router.post("/change-password", status_code=204)
def change_password(payload: ChangePasswordIn, ctx: Ctx = Depends(get_ctx)):
    if not security.verify_password(ctx.user.password_hash, payload.current_password):
        raise HTTPException(status_code=401, detail="Password attuale non corretta")
    ctx.user.password_hash = security.hash_password(payload.new_password)
    ctx.db.commit()


# --- 2FA TOTP opzionale -----------------------------------------------------------
class TotpSetupOut(BaseModel):
    secret: str
    otpauth_uri: str


class TotpCodeIn(BaseModel):
    code: str


class TotpDisableIn(BaseModel):
    password: str


@router.post("/totp/setup", response_model=TotpSetupOut)
def totp_setup(ctx: Ctx = Depends(get_ctx)):
    if ctx.user.totp_enabled:
        raise HTTPException(status_code=409, detail="La verifica a 2 passaggi è già attiva")
    secret = security.new_totp_secret()
    ctx.user.totp_secret = secret
    ctx.db.commit()
    return TotpSetupOut(secret=secret, otpauth_uri=security.totp_uri(secret, ctx.user.email))


@router.post("/totp/enable", status_code=204)
def totp_enable(payload: TotpCodeIn, ctx: Ctx = Depends(get_ctx)):
    if not ctx.user.totp_secret or not security.verify_totp(ctx.user.totp_secret, payload.code):
        raise HTTPException(status_code=422, detail="Codice non valido")
    ctx.user.totp_enabled = True
    ctx.db.commit()


@router.post("/totp/disable", status_code=204)
def totp_disable(payload: TotpDisableIn, ctx: Ctx = Depends(get_ctx)):
    if not security.verify_password(ctx.user.password_hash, payload.password):
        raise HTTPException(status_code=401, detail="Password non corretta")
    ctx.user.totp_enabled = False
    ctx.user.totp_secret = None
    ctx.db.commit()
