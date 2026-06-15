"""Hamster Office — API (FastAPI, Modular Monolith)."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .core.config import settings
from .core.database import engine
from .core.exceptions import register_exception_handlers
from .core.logging import setup_logging
from .core.observability import ObservabilityMiddleware, metrics_response
from .core.realtime import manager
from .core.redis import get_redis
from .integrations import storage
from .modules.admin.router import router as admin_router
from .modules.agents.router import router as agents_router
from .modules.agents.router import runs_router
from .modules.auth.router import router as auth_router
from .modules.chat.router import router as chat_router
from .modules.chat.ws import ws_router
from .modules.knowledge.router import documents_router, knowledge_router
from .modules.office.router import router as office_router
from .modules.projects.router import router as projects_router
from .modules.tasks.router import router as tasks_router
from .modules.workspace.router import router as workspace_router

log = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    await manager.start()
    try:
        storage.ensure_bucket()
    except Exception as e:  # noqa: BLE001
        log.warning("MinIO indisponível no startup: %s", e)
    yield
    await manager.stop()


app = FastAPI(title="Hamster Office API", version="0.1.0", lifespan=lifespan)

app.add_middleware(ObservabilityMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

# REST /api/v1
API = "/api/v1"
for r in (
    auth_router,
    workspace_router,
    projects_router,
    tasks_router,
    chat_router,
    documents_router,
    knowledge_router,
    agents_router,
    runs_router,
    office_router,
    admin_router,
):
    app.include_router(r, prefix=API)

# WebSocket /ws
app.include_router(ws_router)


@app.get("/metrics", tags=["meta"])
async def metrics():
    return metrics_response()


@app.get("/healthz", tags=["meta"])
async def healthz():
    return {"status": "ok"}


@app.get("/readyz", tags=["meta"])
async def readyz():
    checks = {"db": False, "redis": False}
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["db"] = True
    except Exception:  # noqa: BLE001
        pass
    try:
        await get_redis().ping()
        checks["redis"] = True
    except Exception:  # noqa: BLE001
        pass
    ready = all(checks.values())
    return {"ready": ready, "checks": checks}
