"""Audit log di ogni creazione/modifica/disattivazione con valori prima/dopo (RF-14)."""

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel

from app.deps import Ctx
from app.models import AuditLog


def record(
    ctx: Ctx,
    entity: str,
    entity_id: uuid.UUID | None,
    action: str,
    before: dict | None = None,
    after: dict | None = None,
) -> None:
    ctx.db.add(
        AuditLog(
            tenant_id=ctx.tenant_id,
            user_id=ctx.user.id,
            entity=entity,
            entity_id=entity_id,
            action=action,
            before=before,
            after=after,
            ip=ctx.ip,
        )
    )


def snapshot(schema: type[BaseModel], obj: Any) -> dict:
    """Foto JSON dell'oggetto secondo lo schema di uscita."""
    return schema.model_validate(obj).model_dump(mode="json")


def plain(data: dict) -> dict:
    """Converte le enum in valori semplici prima di passarli all'ORM."""
    return {k: (v.value if isinstance(v, Enum) else v) for k, v in data.items()}
