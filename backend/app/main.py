"""SipMate FastAPI application entrypoint."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import admin, auth, gamification, products, profile, recommendations, redemptions, rewards
from app.core.config import get_settings
from app.core.errors import http_exception_handler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("sipmate")

settings = get_settings()

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.add_exception_handler(HTTPException, http_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(products.router, prefix=settings.api_prefix)
app.include_router(recommendations.router, prefix=settings.api_prefix)
app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(profile.router, prefix=settings.api_prefix)
app.include_router(gamification.router, prefix=settings.api_prefix)
app.include_router(rewards.router, prefix=settings.api_prefix)
app.include_router(redemptions.router, prefix=settings.api_prefix)
app.include_router(admin.router, prefix=settings.api_prefix)

upload_dir = Path(settings.local_upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")


@app.on_event("startup")
def on_startup() -> None:
    logger.info(
        "SipMate starting environment=%s cors=%s",
        settings.environment,
        settings.cors_origin_list,
    )
    from app.services.recommendation_service import load_recommender

    model = load_recommender()
    if model is None:
        logger.warning("Recommender artifacts not loaded at startup")
    else:
        logger.info("Recommender ready products=%s", model.n_products)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}


def _mount_frontend() -> None:
    dist = Path(settings.frontend_dist)
    if not settings.frontend_dist or not dist.is_dir():
        logger.info("Frontend dist not mounted (%s)", settings.frontend_dist or "disabled")
        return
    index = dist / "index.html"
    if not index.is_file():
        logger.warning("Frontend dist missing index.html at %s", dist)
        return

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=str(assets)), name="frontend-assets")

    @app.get("/{full_path:path}")
    async def spa_fallback(full_path: str) -> FileResponse:
        candidate = dist / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)

    logger.info("Serving SPA from %s", dist.resolve())


_mount_frontend()
