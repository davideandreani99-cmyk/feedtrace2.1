"""Modello dati F1: tenant, utenti, anagrafiche (RF-01), audit (RF-14).

Quantità: Numeric (mai float). Date in UTC. Ogni tabella operativa ha tenant_id (RLS).
"""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class IdMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class TenantMixin(IdMixin):
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ActiveMixin:
    # Le anagrafiche non si cancellano: si disattivano (RF-01).
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


# --- identità e tenant -------------------------------------------------------------
class Tenant(Base):
    __tablename__ = "tenant"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200))
    vat_number: Mapped[str | None] = mapped_column(String(20), unique=True)
    plan: Mapped[str] = mapped_column(String(30), default="base", server_default="base")
    settings: Mapped[dict] = mapped_column(JSONB, default=dict, server_default="{}")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class AppUser(Base):
    """Utente globale: può appartenere a più tenant tramite Membership."""

    __tablename__ = "app_user"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(200))
    is_superadmin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    totp_secret: Mapped[str | None] = mapped_column(String(64))
    totp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Membership(TenantMixin, Base):
    __tablename__ = "membership"
    __table_args__ = (UniqueConstraint("user_id", "tenant_id"),)

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("app_user.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))


# --- anagrafiche -------------------------------------------------------------------
class Site(TenantMixin, ActiveMixin, Base):
    __tablename__ = "site"
    __table_args__ = (UniqueConstraint("tenant_id", "asl_code"),)

    name: Mapped[str] = mapped_column(String(200))
    asl_code: Mapped[str] = mapped_column(String(20))
    address: Mapped[str | None] = mapped_column(String(300))
    province: Mapped[str | None] = mapped_column(String(50))
    dop_circuit: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")


class Supplier(TenantMixin, ActiveMixin, Base):
    __tablename__ = "supplier"
    __table_args__ = (UniqueConstraint("tenant_id", "vat_number"),)

    name: Mapped[str] = mapped_column(String(200))
    vat_number: Mapped[str | None] = mapped_column(String(20))
    reg_183_number: Mapped[str | None] = mapped_column(String(40))
    medicated_supplier: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )


class RawMaterial(TenantMixin, ActiveMixin, Base):
    __tablename__ = "raw_material"
    __table_args__ = (UniqueConstraint("tenant_id", "code"),)

    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(30))
    unit: Mapped[str] = mapped_column(String(5), default="kg", server_default="kg")
    density_kg_l: Mapped[Decimal | None] = mapped_column(Numeric(8, 4))
    dry_matter_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))
    fat_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))
    linoleic_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))
    dop_category: Mapped[str | None] = mapped_column(String(60))
    requires_analysis: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    lot_tracked: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class Container(TenantMixin, ActiveMixin, Base):
    __tablename__ = "container"
    __table_args__ = (UniqueConstraint("site_id", "code"),)

    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("site.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    type: Mapped[str] = mapped_column(String(20))
    capacity: Mapped[Decimal | None] = mapped_column(Numeric(18, 3))
    unit: Mapped[str] = mapped_column(String(5), default="kg", server_default="kg")
    consumption_policy: Mapped[str] = mapped_column(
        String(20), default="FIFO", server_default="FIFO"
    )
    negative_threshold_kg: Mapped[Decimal] = mapped_column(
        Numeric(18, 3), default=Decimal("0"), server_default="0"
    )
    medicated_only: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    medicated_contaminated: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )


class ContainerAllowedMaterial(TenantMixin, Base):
    __tablename__ = "container_allowed_material"
    __table_args__ = (UniqueConstraint("container_id", "material_id"),)

    container_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("container.id"), index=True)
    material_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raw_material.id"))


class Plant(TenantMixin, ActiveMixin, Base):
    __tablename__ = "plant"
    __table_args__ = (UniqueConstraint("site_id", "code"),)

    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("site.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(25))
    lot_rule: Mapped[str] = mapped_column(
        String(30), default="PER_CICLO", server_default="PER_CICLO"
    )
    tolerance_pct: Mapped[Decimal] = mapped_column(
        Numeric(7, 3), default=Decimal("0"), server_default="0"
    )
    processing_cost_eur_t: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), server_default="0"
    )
    medicated_authorized: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    medicated_contaminated: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )


class Recipe(TenantMixin, ActiveMixin, Base):
    """Una riga per versione: le versioni non si modificano (RF-01)."""

    __tablename__ = "recipe"
    __table_args__ = (UniqueConstraint("tenant_id", "code", "version"),)

    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(200))
    version: Mapped[int] = mapped_column(Integer)
    valid_from: Mapped[date] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)
    plant_type: Mapped[str] = mapped_column(String(25))
    phase: Mapped[str] = mapped_column(String(20), default="ALTRO", server_default="ALTRO")
    dop: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    medicated: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    lines: Mapped[list["RecipeLine"]] = relationship(
        order_by="RecipeLine.position", lazy="select"
    )


class RecipeLine(TenantMixin, Base):
    __tablename__ = "recipe_line"
    __table_args__ = (UniqueConstraint("recipe_id", "material_id"),)

    recipe_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("recipe.id"), index=True)
    material_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("raw_material.id"))
    position: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    kg_per_t: Mapped[Decimal] = mapped_column(Numeric(12, 3))
    default_container_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("container.id"))
    tolerance_pct: Mapped[Decimal | None] = mapped_column(Numeric(7, 3))


class DestinationLot(TenantMixin, ActiveMixin, Base):
    __tablename__ = "destination_lot"
    __table_args__ = (UniqueConstraint("tenant_id", "internal_code"),)

    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("site.id"), index=True)
    internal_code: Mapped[str] = mapped_column(String(40))
    external_code: Mapped[str | None] = mapped_column(String(40), index=True)  # codice Pig'UP
    description: Mapped[str | None] = mapped_column(String(300))
    phase: Mapped[str] = mapped_column(String(20), default="ALTRO", server_default="ALTRO")
    head_count: Mapped[int | None] = mapped_column(Integer)
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)
    dop: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    status: Mapped[str] = mapped_column(String(10), default="APERTO", server_default="APERTO")


class Location(TenantMixin, ActiveMixin, Base):
    """Capannone / sala / box / valvola."""

    __tablename__ = "location"
    __table_args__ = (UniqueConstraint("site_id", "name"),)

    site_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("site.id"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str | None] = mapped_column(String(30))


class Occupancy(TenantMixin, Base):
    __tablename__ = "occupancy"

    location_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("location.id"), index=True)
    destination_lot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("destination_lot.id"), index=True
    )
    date_from: Mapped[date] = mapped_column(Date)
    date_to: Mapped[date | None] = mapped_column(Date)


class AccountingPeriod(TenantMixin, Base):
    """Periodo contabile mensile; la chiusura è usata da F6 (RF-11)."""

    __tablename__ = "accounting_period"
    __table_args__ = (UniqueConstraint("tenant_id", "year", "month"),)

    year: Mapped[int] = mapped_column(Integer)
    month: Mapped[int] = mapped_column(Integer)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --- audit (immutabile: trigger + nessun privilegio UPDATE/DELETE) ------------------
class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenant.id"), index=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("app_user.id"))
    entity: Mapped[str] = mapped_column(String(60), index=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    action: Mapped[str] = mapped_column(String(20))
    before: Mapped[dict | None] = mapped_column(JSONB)
    after: Mapped[dict | None] = mapped_column(JSONB)
    ip: Mapped[str | None] = mapped_column(String(64))
