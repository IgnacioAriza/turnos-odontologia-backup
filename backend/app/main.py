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
    try:
        await init_db()
    except Exception as e:
        logger.error("init_db_error", error=str(e), exc_info=True)
        raise
    yield
    logger.info("application_shutdown")
    await close_db()


def create_app() -> FastAPI:
    """Factory function to create the FastAPI application."""
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
        from app.infrastructure.db.base import get_engine

        db_status = "disconnected"
        redis_status = "disconnected"

        try:
            async with get_engine().connect() as conn:
                await conn.execute(text("SELECT 1"))
            db_status = "connected"
        except Exception as e:
            logger.warning("healthcheck_db_failed", error=str(e))

        try:
            r = redis.from_url(settings.redis_url)
            await r.ping()
            await r.close()
            redis_status = "connected"
        except Exception as e:
            logger.warning("healthcheck_redis_failed", error=str(e))

        return {
            "status": "ok",
            "service": "turnos-odontologia-api",
            "database": db_status,
            "redis": redis_status,
        }

    # Import all domain models and routers
    from app.api.auth import router as auth_router
    from app.domain.auth import models as _auth_models  # noqa: F401
    from app.domain.clinica import models as _clinica_models  # noqa: F401
    from app.domain.personas import models as _personas_models  # noqa: F401

    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

    return app


app = create_app()
