import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app import audit, security
from app.crud import flush_or_409
from app.deps import Ctx, require
from app.models import AppUser, AuditLog, Membership
from domain.permissions import Permission, Role

router = APIRouter(tags=["users"])

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"


class UserOut(BaseModel):
    membership_id: uuid.UUID
    user_id: uuid.UUID
    email: str
    full_name: str
    role: Role


class UserIn(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=320)
    full_name: str = Field(min_length=1, max_length=200)
    password: str | None = Field(None, min_length=10, max_length=200)
    role: Role


class RoleIn(BaseModel):
    role: Role


def _out(membership: Membership, user: AppUser) -> UserOut:
    return UserOut(
        membership_id=membership.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=Role(membership.role),
    )


def _load(ctx: Ctx, membership_id: uuid.UUID) -> tuple[Membership, AppUser]:
    row = ctx.db.execute(
        select(Membership, AppUser)
        .join(AppUser, AppUser.id == Membership.user_id)
        .where(Membership.id == membership_id, Membership.tenant_id == ctx.tenant_id)
    ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Utente non trovato")
    return row[0], row[1]


def _other_admins(ctx: Ctx, membership_id: uuid.UUID) -> int:
    return ctx.db.scalar(
        select(func.count())
        .select_from(Membership)
        .where(
            Membership.tenant_id == ctx.tenant_id,
            Membership.role == Role.ADMIN.value,
            Membership.id != membership_id,
        )
    ) or 0


@router.get("/users", response_model=list[UserOut])
def list_users(ctx: Ctx = Depends(require(Permission.USERS_MANAGE))):
    rows = ctx.db.execute(
        select(Membership, AppUser)
        .join(AppUser, AppUser.id == Membership.user_id)
        .where(Membership.tenant_id == ctx.tenant_id)
        .order_by(AppUser.email)
    ).all()
    return [_out(m, u) for m, u in rows]


@router.post("/users", response_model=UserOut, status_code=201)
def add_user(payload: UserIn, ctx: Ctx = Depends(require(Permission.USERS_MANAGE))):
    """Aggiunge un utente al tenant (lo crea se l'email non esiste ancora)."""
    email = payload.email.strip().lower()
    user = ctx.db.scalar(select(AppUser).where(AppUser.email == email))
    if user is None:
        if not payload.password:
            raise HTTPException(
                status_code=422, detail="La password è obbligatoria per un nuovo utente"
            )
        user = AppUser(
            email=email,
            full_name=payload.full_name,
            password_hash=security.hash_password(payload.password),
        )
        ctx.db.add(user)
        ctx.db.flush()
    else:
        already = ctx.db.scalar(
            select(func.count())
            .select_from(Membership)
            .where(Membership.user_id == user.id, Membership.tenant_id == ctx.tenant_id)
        )
        if already:
            raise HTTPException(status_code=409, detail="Utente già presente in questa azienda")
    membership = Membership(tenant_id=ctx.tenant_id, user_id=user.id, role=payload.role.value)
    ctx.db.add(membership)
    flush_or_409(ctx.db)
    result = _out(membership, user)
    audit.record(
        ctx, "users", membership.id, "CREATE", None, result.model_dump(mode="json")
    )
    ctx.db.commit()
    return result


@router.patch("/users/{membership_id}", response_model=UserOut)
def change_role(
    membership_id: uuid.UUID,
    payload: RoleIn,
    ctx: Ctx = Depends(require(Permission.USERS_MANAGE)),
):
    membership, user = _load(ctx, membership_id)
    if (
        membership.role == Role.ADMIN.value
        and payload.role != Role.ADMIN
        and _other_admins(ctx, membership.id) == 0
    ):
        raise HTTPException(
            status_code=409, detail="Deve restare almeno un amministratore per l'azienda"
        )
    before = _out(membership, user).model_dump(mode="json")
    membership.role = payload.role.value
    flush_or_409(ctx.db)
    result = _out(membership, user)
    audit.record(ctx, "users", membership.id, "UPDATE", before, result.model_dump(mode="json"))
    ctx.db.commit()
    return result


@router.delete("/users/{membership_id}", status_code=204)
def remove_user(
    membership_id: uuid.UUID, ctx: Ctx = Depends(require(Permission.USERS_MANAGE))
):
    """Rimuove l'utente dall'azienda (l'identità globale resta)."""
    membership, user = _load(ctx, membership_id)
    if membership.role == Role.ADMIN.value and _other_admins(ctx, membership.id) == 0:
        raise HTTPException(
            status_code=409, detail="Deve restare almeno un amministratore per l'azienda"
        )
    before = _out(membership, user).model_dump(mode="json")
    ctx.db.delete(membership)
    ctx.db.flush()
    audit.record(ctx, "users", membership_id, "REMOVE", before, None)
    ctx.db.commit()


# --- consultazione audit log -------------------------------------------------------
@router.get("/audit-log")
def list_audit(
    entity: str | None = None,
    entity_id: uuid.UUID | None = None,
    limit: int = 100,
    ctx: Ctx = Depends(require(Permission.AUDIT_READ)),
):
    limit = max(1, min(limit, 500))
    stmt = select(AuditLog).where(AuditLog.tenant_id == ctx.tenant_id)
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    if entity_id:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    rows = ctx.db.scalars(stmt.order_by(AuditLog.at.desc()).limit(limit))
    return [
        {
            "id": str(r.id),
            "at": r.at.isoformat(),
            "user_id": str(r.user_id) if r.user_id else None,
            "entity": r.entity,
            "entity_id": str(r.entity_id) if r.entity_id else None,
            "action": r.action,
            "before": r.before,
            "after": r.after,
            "ip": r.ip,
        }
        for r in rows
    ]
