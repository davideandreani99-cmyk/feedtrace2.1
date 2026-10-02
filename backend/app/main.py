from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.config import settings
from app.db import engine
from app.routers import auth, imports, masterdata, recipes, users

app = FastAPI(
    title="FeedTrace API",
    version="0.1.0",
    description="Tracciabilità dei mangimi per allevamenti suinicoli. Fase 1: fondamenta.",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api/v1")
api.include_router(auth.router)
api.include_router(users.router)
api.include_router(masterdata.router)
api.include_router(recipes.router)
api.include_router(imports.router)
app.include_router(api)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", tags=["system"])
def ready() -> dict[str, str]:
    with engine.connect() as connection:
        connection.execute(text("select 1"))
    return {"status": "ready"}
