import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select

from app import audit
from app.crud import check_refs, crud_router, flush_or_409
from app.deps import Ctx, require
from app.models import (
    Container,
    ContainerAllowedMaterial,
    DestinationLot,
    Location,
    Occupancy,
    Plant,
    RawMaterial,
    Site,
    Supplier,
)
from app.schemas import (
    ContainerIn,
    ContainerOut,
    DestinationLotIn,
    DestinationLotOut,
    LocationIn,
    LocationOut,
    OccupancyIn,
    OccupancyOut,
    OccupancyUpdate,
    PlantIn,
    PlantOut,
    RawMaterialIn,
    RawMaterialOut,
    SiteIn,
    SiteOut,
    SupplierIn,
    SupplierOut,
)
from domain.periods import ranges_overlap
from domain.permissions import Permission

router = APIRouter()

router.include_router(
    crud_router(name="sites", model=Site, create=SiteIn, out=SiteOut, order_by=("name",))
)
router.include_router(
    crud_router(
        name="suppliers", model=Supplier, create=SupplierIn, out=SupplierOut, order_by=("name",)
    )
)
router.include_router(
    crud_router(
        name="raw-materials",
        model=RawMaterial,
        create=RawMaterialIn,
        out=RawMaterialOut,
        order_by=("code",),
    )
)
router.include_router(
    crud_router(
        name="containers",
        model=Container,
        create=ContainerIn,
        out=ContainerOut,
        refs={"site_id": Site},
        order_by=("code",),
    )
)
router.include_router(
    crud_router(
        name="plants",
        model=Plant,
        create=PlantIn,
        out=PlantOut,
        refs={"site_id": Site},
        order_by=("code",),
    )
)
router.include_router(
    crud_router(
        name="destination-lots",
        model=DestinationLot,
        create=DestinationLotIn,
        out=DestinationLotOut,
        refs={"site_id": Site},
        order_by=("internal_code",),
    )
)
router.include_router(
    crud_router(
        name="locations",
        model=Location,
        create=LocationIn,
        out=LocationOut,
        refs={"site_id": Site},
        order_by=("name",),
    )
)


# --- materiali ammessi in un contenitore (SPEC §5) ---------------------------------
def _load_container(ctx: Ctx, container_id: uuid.UUID) -> Container:
    container = ctx.db.scalar(
        select(Container).where(
            Container.id == container_id, Container.tenant_id == ctx.tenant_id
        )
    )
    if container is None:
        raise HTTPException(status_code=404, detail="Contenitore non trovato")
    return container


@router.get("/containers/{container_id}/allowed-materials", response_model=list[uuid.UUID])
def get_allowed_materials(
    container_id: uuid.UUID, ctx: Ctx = Depends(require(Permission.MASTERDATA_READ))
):
    _load_container(ctx, container_id)
    return list(
        ctx.db.scalars(
            select(ContainerAllowedMaterial.material_id).where(
                ContainerAllowedMaterial.container_id == container_id,
                ContainerAllowedMaterial.tenant_id == ctx.tenant_id,
            )
        )
    )


@router.put("/containers/{container_id}/allowed-materials", response_model=list[uuid.UUID])
def set_allowed_materials(
    container_id: uuid.UUID,
    material_ids: list[uuid.UUID],
    ctx: Ctx = Depends(require(Permission.MASTERDATA_WRITE)),
):
    """Sostituisce l'elenco dei materiali ammessi (lista vuota = nessuna restrizione)."""
    _load_container(ctx, container_id)
    unique_ids = list(dict.fromkeys(material_ids))
    for material_id in unique_ids:
        check_refs(ctx, {"material_id": RawMaterial}, {"material_id": material_id})
    before = list(
        ctx.db.scalars(
            select(ContainerAllowedMaterial.material_id).where(
                ContainerAllowedMaterial.container_id == container_id
            )
        )
    )
    ctx.db.execute(
        delete(ContainerAllowedMaterial).where(
            ContainerAllowedMaterial.container_id == container_id,
            ContainerAllowedMaterial.tenant_id == ctx.tenant_id,
        )
    )
    for material_id in unique_ids:
        ctx.db.add(
            ContainerAllowedMaterial(
                tenant_id=ctx.tenant_id, container_id=container_id, material_id=material_id
            )
        )
    flush_or_409(ctx.db)
    audit.record(
        ctx,
        "containers",
        container_id,
        "SET_ALLOWED_MATERIALS",
        {"material_ids": [str(m) for m in before]},
        {"material_ids": [str(m) for m in unique_ids]},
    )
    ctx.db.commit()
    return unique_ids


# --- occupazioni dei luoghi (RF-05: luogo -> lotto di destinazione) -----------------
occupancy_router = APIRouter(prefix="/occupancies", tags=["occupancies"])


@occupancy_router.get("", response_model=list[OccupancyOut])
def list_occupancies(
    location_id: uuid.UUID | None = None,
    destination_lot_id: uuid.UUID | None = None,
    ctx: Ctx = Depends(require(Permission.MASTERDATA_READ)),
):
    stmt = select(Occupancy).where(Occupancy.tenant_id == ctx.tenant_id)
    if location_id:
        stmt = stmt.where(Occupancy.location_id == location_id)
    if destination_lot_id:
        stmt = stmt.where(Occupancy.destination_lot_id == destination_lot_id)
    return list(ctx.db.scalars(stmt.order_by(Occupancy.date_from)))


@occupancy_router.post("", response_model=OccupancyOut, status_code=201)
def create_occupancy(
    payload: OccupancyIn, ctx: Ctx = Depends(require(Permission.MASTERDATA_WRITE))
):
    data = payload.model_dump()
    check_refs(ctx, {"location_id": Location, "destination_lot_id": DestinationLot}, data)
    if payload.date_to is not None and payload.date_to < payload.date_from:
        raise HTTPException(status_code=422, detail="La data fine precede la data inizio")
    existing = ctx.db.scalars(
        select(Occupancy).where(
            Occupancy.location_id == payload.location_id, Occupancy.tenant_id == ctx.tenant_id
        )
    )
    for other in existing:
        if ranges_overlap(payload.date_from, payload.date_to, other.date_from, other.date_to):
            raise HTTPException(
                status_code=409, detail="Il luogo è già occupato nel periodo indicato"
            )
    obj = Occupancy(tenant_id=ctx.tenant_id, **data)
    ctx.db.add(obj)
    flush_or_409(ctx.db)
    ctx.db.refresh(obj)
    audit.record(ctx, "occupancies", obj.id, "CREATE", None, audit.snapshot(OccupancyOut, obj))
    ctx.db.commit()
    return obj


@occupancy_router.patch("/{occupancy_id}", response_model=OccupancyOut)
def close_occupancy(
    occupancy_id: uuid.UUID,
    payload: OccupancyUpdate,
    ctx: Ctx = Depends(require(Permission.MASTERDATA_WRITE)),
):
    """Imposta/modifica la data di fine di un'occupazione."""
    obj = ctx.db.scalar(
        select(Occupancy).where(
            Occupancy.id == occupancy_id, Occupancy.tenant_id == ctx.tenant_id
        )
    )
    if obj is None:
        raise HTTPException(status_code=404, detail="Occupazione non trovata")
    if payload.date_to is not None and payload.date_to < obj.date_from:
        raise HTTPException(status_code=422, detail="La data fine precede la data inizio")
    before = audit.snapshot(OccupancyOut, obj)
    obj.date_to = payload.date_to
    others = ctx.db.scalars(
        select(Occupancy).where(
            Occupancy.location_id == obj.location_id,
            Occupancy.tenant_id == ctx.tenant_id,
            Occupancy.id != obj.id,
        )
    )
    for other in others:
        if ranges_overlap(obj.date_from, obj.date_to, other.date_from, other.date_to):
            ctx.db.rollback()
            raise HTTPException(
                status_code=409, detail="Il luogo è già occupato nel periodo indicato"
            )
    flush_or_409(ctx.db)
    ctx.db.refresh(obj)
    audit.record(
        ctx, "occupancies", obj.id, "UPDATE", before, audit.snapshot(OccupancyOut, obj)
    )
    ctx.db.commit()
    return obj


router.include_router(occupancy_router)
