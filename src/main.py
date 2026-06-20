from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from api_v1 import router as router_v1
from core.config import settings
from core.container import get_container
from core.models.db_helper import db_helper


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        yield
    finally:
        await get_container().creative_preview_client().aclose()
        await get_container().meta_client().aclose()
        await db_helper.engine.dispose()


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router_v1, prefix=settings.api_v1_prefix)


@app.get("/health/live", include_in_schema=False)
async def health_live() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready", include_in_schema=False)
async def health_ready() -> dict[str, str]:
    try:
        async with db_helper.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database is unavailable") from exc
    return {"status": "ok"}
