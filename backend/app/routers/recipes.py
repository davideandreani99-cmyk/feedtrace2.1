import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select

from app import audit
from app.crud import check_refs, flush_or_409
from app.deps import Ctx, require
from app.models import Container, RawMaterial, Recipe, RecipeLine
from app.schemas import RecipeIn, RecipeOut
from domain.permissions import Permission
from domain.recipes import plan_new_version

router = APIRouter(prefix="/recipes", tags=["recipes"])


def _validate_lines(ctx: Ctx, payload: RecipeIn) -> None:
    seen: set[uuid.UUID] = set()
    for line in payload.lines:
        if line.material_id in seen:
            raise HTTPException(
                status_code=422, detail="Materia prima ripetuta nelle righe della ricetta"
            )
        seen.add(line.material_id)
        check_refs(
            ctx,
            {"material_id": RawMaterial, "default_container_id": Container},
            {"material_id": line.material_id, "default_container_id": line.default_container_id},
        )


def create_recipe_version(
    ctx: Ctx, payload: RecipeIn, *, version: int, valid_from: date
) -> Recipe:
    """Inserisce una versione di ricetta con le sue righe (riusata anche dall'import)."""
    recipe = Recipe(
        tenant_id=ctx.tenant_id,
        code=payload.code,
        name=payload.name,
        version=version,
        valid_from=valid_from,
        plant_type=payload.plant_type.value,
        phase=payload.phase.value,
        dop=payload.dop,
        medicated=payload.medicated,
    )
    ctx.db.add(recipe)
    ctx.db.flush()
    for position, line in enumerate(payload.lines):
        ctx.db.add(
            RecipeLine(
                tenant_id=ctx.tenant_id,
                recipe_id=recipe.id,
                material_id=line.material_id,
                position=position,
                kg_per_t=line.kg_per_t,
                default_container_id=line.default_container_id,
                tolerance_pct=line.tolerance_pct,
            )
        )
    flush_or_409(ctx.db)
    ctx.db.refresh(recipe)
    return recipe


def _load(ctx: Ctx, recipe_id: uuid.UUID) -> Recipe:
    recipe = ctx.db.scalar(
        select(Recipe).where(Recipe.id == recipe_id, Recipe.tenant_id == ctx.tenant_id)
    )
    if recipe is None:
        raise HTTPException(status_code=404, detail="Ricetta non trovata")
    return recipe


@router.get("", response_model=list[RecipeOut])
def list_recipes(
    all_versions: bool = False,
    code: str | None = None,
    ctx: Ctx = Depends(require(Permission.MASTERDATA_READ)),
):
    """Per default solo l'ultima versione di ogni ricetta."""
    stmt = select(Recipe).where(Recipe.tenant_id == ctx.tenant_id)
    if code:
        stmt = stmt.where(Recipe.code == code)
    if not all_versions:
        latest = (
            select(Recipe.code, func.max(Recipe.version).label("v"))
            .where(Recipe.tenant_id == ctx.tenant_id)
            .group_by(Recipe.code)
            .subquery()
        )
        stmt = stmt.join(
            latest, (Recipe.code == latest.c.code) & (Recipe.version == latest.c.v)
        )
    rows = ctx.db.scalars(stmt.order_by(Recipe.code, Recipe.version))
    return [RecipeOut.model_validate(r) for r in rows]


@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(recipe_id: uuid.UUID, ctx: Ctx = Depends(require(Permission.MASTERDATA_READ))):
    return RecipeOut.model_validate(_load(ctx, recipe_id))


@router.post("", response_model=RecipeOut, status_code=201)
def create_recipe(payload: RecipeIn, ctx: Ctx = Depends(require(Permission.MASTERDATA_WRITE))):
    exists = ctx.db.scalar(
        select(func.count())
        .select_from(Recipe)
        .where(Recipe.tenant_id == ctx.tenant_id, Recipe.code == payload.code)
    )
    if exists:
        raise HTTPException(
            status_code=409,
            detail="Esiste già una ricetta con questo codice: modificala per creare una versione",
        )
    _validate_lines(ctx, payload)
    recipe = create_recipe_version(
        ctx, payload, version=1, valid_from=payload.valid_from or date.today()
    )
    result = RecipeOut.model_validate(recipe)  # prima del commit (RLS e relazioni)
    audit.record(ctx, "recipes", recipe.id, "CREATE", None, result.model_dump(mode="json"))
    ctx.db.commit()
    return result


@router.put("/{recipe_id}", response_model=RecipeOut)
def new_recipe_version(
    recipe_id: uuid.UUID,
    payload: RecipeIn,
    ctx: Ctx = Depends(require(Permission.MASTERDATA_WRITE)),
):
    """Una modifica crea una NUOVA versione; le versioni precedenti restano intatte."""
    current = _load(ctx, recipe_id)
    latest_version = ctx.db.scalar(
        select(func.max(Recipe.version)).where(
            Recipe.tenant_id == ctx.tenant_id, Recipe.code == current.code
        )
    )
    if current.version != latest_version:
        raise HTTPException(
            status_code=409, detail="Si può modificare solo l'ultima versione della ricetta"
        )
    if payload.code != current.code:
        raise HTTPException(status_code=422, detail="Il codice ricetta non può cambiare")
    _validate_lines(ctx, payload)
    new_from = payload.valid_from or date.today()
    try:
        version, previous_valid_to = plan_new_version(
            current.version, current.valid_from, new_from
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    before = RecipeOut.model_validate(current).model_dump(mode="json")
    current.valid_to = previous_valid_to
    recipe = create_recipe_version(ctx, payload, version=version, valid_from=new_from)
    result = RecipeOut.model_validate(recipe)
    audit.record(
        ctx, "recipes", recipe.id, "NEW_VERSION", before, result.model_dump(mode="json")
    )
    ctx.db.commit()
    return result


@router.delete("/{recipe_id}", response_model=RecipeOut)
def deactivate_recipe(
    recipe_id: uuid.UUID, ctx: Ctx = Depends(require(Permission.MASTERDATA_WRITE))
):
    """Disattiva tutte le versioni della ricetta (le produzioni passate restano valide)."""
    current = _load(ctx, recipe_id)
    versions = list(
        ctx.db.scalars(
            select(Recipe).where(Recipe.tenant_id == ctx.tenant_id, Recipe.code == current.code)
        )
    )
    before = RecipeOut.model_validate(current).model_dump(mode="json")
    for recipe in versions:
        recipe.active = False
    flush_or_409(ctx.db)
    ctx.db.refresh(current)
    result = RecipeOut.model_validate(current)
    audit.record(
        ctx, "recipes", current.id, "DEACTIVATE", before, result.model_dump(mode="json")
    )
    ctx.db.commit()
    return result
