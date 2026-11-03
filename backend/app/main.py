from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.infrastructure.db.base import close_db, init_db

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("application_startup")
    await init_db()
    yield
    logger.info("application_shutdown")
    await close_db()


app = FastAPI(
    title="Turnos Odontología API",
    description="SaaS para gestión de turnos odontológicos",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)


@app.get("/api/health", tags=["health"])
async def health_check() -> dict[str, str]:
    import redis.asyncio as redis

    from app.core.config import settings
    from app.infrastructure.db.base import engine

    db_status = "disconnected"
    redis_status = "disconnected"

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        pass

    try:
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.close()
        redis_status = "connected"
    except Exception:
        pass

    return {
        "status": "ok",
        "service": "turnos-odontologia-api",
        "database": db_status,
        "redis": redis_status,
    }


from app.api.auth import router as auth_router

# Placeholder for router imports - will be added in C-02+
# from app.api.public import router as public_router
# from app.api.internal import router as internal_router
# from app.api.webhooks import router as webhooks_router
#
# app.include_router(public_router, prefix="/api")
# app.include_router(internal_router, prefix="/api/internal")
# app.include_router(webhooks_router, prefix="/api/webhooks")

app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
