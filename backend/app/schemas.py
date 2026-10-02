"""Schemi di ingresso/uscita delle anagrafiche (RF-01). Quantita: Decimal, mai float."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator

from domain.enums import (
    ConsumptionPolicy,
    ContainerType,
    DestinationLotStatus,
    LotRule,
    MaterialType,
    Phase,
    PlantType,
    Unit,
)

Name = Annotated[str, Field(min_length=1, max_length=200)]
Code = Annotated[str, Field(min_length=1, max_length=40)]
Pct = Annotated[Decimal, Field(ge=0, le=100, max_digits=7, decimal_places=3)]
NonNeg = Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=4)]


class OutBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    active: bool
    created_at: datetime


def make_update(create: type[BaseModel]) -> type[BaseModel]:
    """Schema PATCH: tutti i campi opzionali (+ `active` per la riattivazione)."""
    fields: dict = {}
    for name, info in create.model_fields.items():
        annotation = info.annotation
        if info.metadata:
            annotation = Annotated[annotation, *info.metadata]
        fields[name] = (Optional[annotation], None)  # noqa: UP045
    fields["active"] = (Optional[bool], None)  # noqa: UP045
    return create_model(f"{create.__name__}Update", **fields)


# --- sito --------------------------------------------------------------------------
class SiteIn(BaseModel):
    name: Name
    asl_code: Annotated[str, Field(min_length=1, max_length=20)]
    address: str | None = Field(None, max_length=300)
    province: str | None = Field(None, max_length=50)
    dop_circuit: bool = False


class SiteOut(OutBase, SiteIn):
    pass


# --- fornitore ---------------------------------------------------------------------
class SupplierIn(BaseModel):
    name: Name
    vat_number: str | None = Field(None, max_length=20)
    reg_183_number: str | None = Field(None, max_length=40)
    medicated_supplier: bool = False


class SupplierOut(OutBase, SupplierIn):
    pass


# --- materia prima -----------------------------------------------------------------
class RawMaterialIn(BaseModel):
    code: Code
    name: Name
    type: MaterialType
    unit: Unit = Unit.KG
    density_kg_l: Decimal | None = Field(None, gt=0, max_digits=8, decimal_places=4)
    dry_matter_pct: Pct | None = None
    fat_pct: Pct | None = None
    linoleic_pct: Pct | None = None
    dop_category: str | None = Field(None, max_length=60)
    requires_analysis: bool = False
    lot_tracked: bool = True

    @model_validator(mode="after")
    def liquidi_con_densita(self) -> "RawMaterialIn":
        if self.unit == Unit.L and self.density_kg_l is None:
            raise ValueError("Per le materie prime in litri la densità (kg/l) è obbligatoria")
        return self


class RawMaterialOut(OutBase, RawMaterialIn):
    pass


# --- contenitore -------------------------------------------------------------------
class ContainerIn(BaseModel):
    site_id: uuid.UUID
    code: Code
    type: ContainerType
    capacity: Decimal | None = Field(None, ge=0, max_digits=18, decimal_places=3)
    unit: Unit = Unit.KG
    consumption_policy: ConsumptionPolicy = ConsumptionPolicy.FIFO
    negative_threshold_kg: Decimal = Field(Decimal("0"), ge=0, max_digits=18, decimal_places=3)
    medicated_only: bool = False


class ContainerOut(OutBase, ContainerIn):
    medicated_contaminated: bool  # stato gestito dal sistema (F6)


# --- impianto ----------------------------------------------------------------------
class PlantIn(BaseModel):
    site_id: uuid.UUID
    code: Code
    name: Name
    type: PlantType
    lot_rule: LotRule = LotRule.PER_CICLO
    tolerance_pct: Pct = Decimal("0")
    processing_cost_eur_t: NonNeg = Decimal("0")
    medicated_authorized: bool = False


class PlantOut(OutBase, PlantIn):
    medicated_contaminated: bool


# --- lotto di destinazione ---------------------------------------------------------
class DestinationLotIn(BaseModel):
    site_id: uuid.UUID
    internal_code: Code
    external_code: str | None = Field(None, max_length=40)  # codice Pig'UP
    description: str | None = Field(None, max_length=300)
    phase: Phase = Phase.ALTRO
    head_count: int | None = Field(None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
    dop: bool = False
    status: DestinationLotStatus = DestinationLotStatus.APERTO


class DestinationLotOut(OutBase, DestinationLotIn):
    pass


# --- luogo e occupazione -----------------------------------------------------------
class LocationIn(BaseModel):
    site_id: uuid.UUID
    name: Annotated[str, Field(min_length=1, max_length=100)]
    kind: str | None = Field(None, max_length=30)


class LocationOut(OutBase, LocationIn):
    pass


class OccupancyIn(BaseModel):
    location_id: uuid.UUID
    destination_lot_id: uuid.UUID
    date_from: date
    date_to: date | None = None


class OccupancyUpdate(BaseModel):
    date_to: date | None = None


class OccupancyOut(OccupancyIn):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime


# --- ricetta -----------------------------------------------------------------------
class RecipeLineIn(BaseModel):
    material_id: uuid.UUID
    kg_per_t: Decimal = Field(gt=0, max_digits=12, decimal_places=3)
    default_container_id: uuid.UUID | None = None
    tolerance_pct: Pct | None = None


class RecipeLineOut(RecipeLineIn):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID


class RecipeIn(BaseModel):
    code: Code
    name: Name
    plant_type: PlantType
    phase: Phase = Phase.ALTRO
    dop: bool = False
    medicated: bool = False
    valid_from: date | None = None  # default: oggi
    lines: list[RecipeLineIn] = Field(min_length=1)


class RecipeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    version: int
    valid_from: date
    valid_to: date | None
    plant_type: PlantType
    phase: Phase
    dop: bool
    medicated: bool
    active: bool
    created_at: datetime
    lines: list[RecipeLineOut]
