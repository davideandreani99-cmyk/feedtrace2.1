from dataclasses import asdict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app import importing
from app.deps import Ctx, require
from domain.permissions import Permission

router = APIRouter(prefix="/imports", tags=["imports"])


class RowErrorOut(BaseModel):
    line: int
    message: str


class ImportOut(BaseModel):
    entity: str
    total: int
    ok: int
    errors: list[RowErrorOut]
    applied: bool


@router.post("/{entity}", response_model=ImportOut)
async def import_file(
    entity: str,
    confirm: bool = False,
    file: UploadFile = File(...),
    ctx: Ctx = Depends(require(Permission.IMPORT_RUN)),
):
    """Anteprima (confirm=false) o applicazione (confirm=true) di un import CSV/XLSX."""
    if entity not in importing.ENTITIES:
        raise HTTPException(
            status_code=404,
            detail=f"Entità non importabile. Ammesse: {', '.join(importing.ENTITIES)}",
        )
    content = await file.read()
    if len(content) > importing.MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File troppo grande (massimo 5 MB)")
    try:
        rows = importing.read_rows(file.filename or "", content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:  # file corrotto
        raise HTTPException(status_code=422, detail="File non leggibile") from exc
    if not rows:
        raise HTTPException(status_code=422, detail="Il file non contiene righe")
    result = importing.run_import(ctx, entity, rows, confirm=confirm)
    return ImportOut(**asdict(result))
