"""Nakshion API app factory."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.errors import install_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import (
    BodyLimitMiddleware,
    CatchAllMiddleware,
    GlobalRateLimitMiddleware,
    PathNormaliseMiddleware,
    RequestContextMiddleware,
)
from app.routers import auth, charts, chat, compatibility, geocoding, health, horoscopes, internal, panchang, users
from app.services import ai, cache, email_service, engine

log = logging.getLogger("app")

API_PREFIX = "/api/v1"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    if engine.engine_available():
        ok = await engine.self_test()
        log.info("engine_self_test", extra={"ok": ok, "engine_version": engine.engine_version()})
    else:
        log.error("engine_unavailable")  # readiness reports it; charts return CHART_CALCULATION_FAILED
    ai.configure_pipeline()
    await ai.rag_startup_check()  # warns, never blocks boot
    yield
    await email_service.drain()
    await cache.close()
    engine.astro_executor.shutdown(wait=False, cancel_futures=True)


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        redirect_slashes=False,
        lifespan=lifespan,
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None,
        openapi_url=None if settings.is_production else "/openapi.json",
    )
    install_exception_handlers(app)

    for r in (auth.router, users.router, charts.router, chat.router, compatibility.router,
              horoscopes.router, geocoding.router, panchang.router):
        app.include_router(r, prefix=API_PREFIX)
    app.include_router(health.router)                     # /health, /health/live, /health/ready
    app.include_router(health.router, prefix=API_PREFIX)  # also under /api/v1
    app.include_router(internal.router)                   # /internal/cron/{job}

    # Added innermost -> outermost. Request path: context -> CORS -> global limit -> normalise -> app.
    app.add_middleware(CatchAllMiddleware)
    app.add_middleware(PathNormaliseMiddleware)
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(GlobalRateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Retry-After", "X-Request-Id"],
        max_age=600,
    )
    app.add_middleware(RequestContextMiddleware)
    return app


app = create_app()
