"""Router CRUD generico per le anagrafiche: tenant, permessi, audit, disattivazione logica."""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import audit
from app.deps import Ctx, require
from app.schemas import make_update
from domain.permissions import Permission


def flush_or_409(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Violazione di un vincolo: elemento già esistente o riferimento non valido",
        ) from exc


def check_refs(ctx: Ctx, refs: dict[str, Any], data: dict[str, Any]) -> None:
    """Le chiavi esterne devono puntare a record visibili al tenant corrente.

    Necessario perche' i controlli FK di PostgreSQL non passano dalla RLS.
    """
    for field, ref_model in refs.items():
        value = data.get(field)
        if value is not None and ctx.db.get(ref_model, value) is None:
            raise HTTPException(status_code=422, detail=f"Riferimento non valido: {field}")


def crud_router(
    *,
    name: str,
    model: Any,
    create: type[BaseModel],
    out: type[BaseModel],
    refs: dict[str, Any] | None = None,
    order_by: tuple[str, ...] = ("created_at",),
) -> APIRouter:
    update = make_update(create)
    refs = refs or {}
    router = APIRouter(prefix=f"/{name}", tags=[name])

    def load(ctx: Ctx, item_id: uuid.UUID) -> Any:
        obj = ctx.db.scalar(
            select(model).where(model.id == item_id, model.tenant_id == ctx.tenant_id)
        )
        if obj is None:
            raise HTTPException(status_code=404, detail="Elemento non trovato")
        return obj

    @router.get("", response_model=list[out])
    def list_items(
        active: bool | None = None,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
        ctx: Ctx = Depends(require(Permission.MASTERDATA_READ)),
    ):
        stmt = select(model).where(model.tenant_id == ctx.tenant_id)
        if active is not None:
            stmt = stmt.where(model.active == active)
        stmt = stmt.order_by(*[getattr(model, c) for c in order_by]).limit(limit).offset(offset)
        return list(ctx.db.scalars(stmt))

    @router.get("/{item_id}", response_model=out)
    def get_item(
        item_id: uuid.UUID, ctx: Ctx = Depends(require(Permission.MASTERDATA_READ))
    ):
        return load(ctx, item_id)

    @router.post("", response_model=out, status_code=201)
    def create_item(
        payload: create,  # type: ignore[valid-type]
        ctx: Ctx = Depends(require(Permission.MASTERDATA_WRITE)),
    ):
        data = audit.plain(payload.model_dump())
        check_refs(ctx, refs, data)
        obj = model(tenant_id=ctx.tenant_id, **data)
        ctx.db.add(obj)
        flush_or_409(ctx.db)
        ctx.db.refresh(obj)
        audit.record(ctx, name, obj.id, "CREATE", None, audit.snapshot(out, obj))
        ctx.db.commit()
        return obj

    @router.patch("/{item_id}", response_model=out)
    def update_item(
        item_id: uuid.UUID,
        payload: update,  # type: ignore[valid-type]
        ctx: Ctx = Depends(require(Permission.MASTERDATA_WRITE)),
    ):
        obj = load(ctx, item_id)
        data = audit.plain(payload.model_dump(exclude_unset=True))
        check_refs(ctx, refs, data)
        before = audit.snapshot(out, obj)
        for key, value in data.items():
            setattr(obj, key, value)
        flush_or_409(ctx.db)
        ctx.db.refresh(obj)
        audit.record(ctx, name, obj.id, "UPDATE", before, audit.snapshot(out, obj))
        ctx.db.commit()
        return obj

    @router.delete("/{item_id}", response_model=out)
    def deactivate_item(
        item_id: uuid.UUID, ctx: Ctx = Depends(require(Permission.MASTERDATA_WRITE))
    ):
        """Cancellazione logica: l'anagrafica viene disattivata, mai eliminata."""
        obj = load(ctx, item_id)
        before = audit.snapshot(out, obj)
        obj.active = False
        flush_or_409(ctx.db)
        ctx.db.refresh(obj)
        audit.record(ctx, name, obj.id, "DEACTIVATE", before, audit.snapshot(out, obj))
        ctx.db.commit()
        return obj

    return router
