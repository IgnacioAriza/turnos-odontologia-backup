from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_async_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """Obtener o crear el engine de base de datos de forma lazy."""
    global _engine
    if _engine is None:
        if "sqlite" in settings.database_url:
            _engine = create_async_engine(
                settings.database_url,
                echo=False,
                connect_args={"check_same_thread": False},
            )
        else:
            _engine = create_async_engine(
                settings.database_url, echo=False, pool_pre_ping=True, pool_size=10, max_overflow=20
            )
    return _engine


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Obtener o crear la factory de sesiones de forma lazy."""
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False, autoflush=False
        )
    return _async_session_factory


# Para compatibilidad hacia atrás, crear propiedades de módulo
# que se evalúan de forma lazy al accederse
class _ModuleLazy:
    """Wrapper para acceso lazy a engine y async_session_factory."""

    @property
    def engine(self) -> AsyncEngine:
        return get_engine()

    @property
    def async_session_factory(self) -> async_sessionmaker[AsyncSession]:
        return get_async_session_factory()


# Instancia lazy para importación hacia atrás
_lazy = _ModuleLazy()


def __getattr__(name: str) -> Any:
    """Soportar importación directa de engine y async_session_factory."""
    if name == "engine":
        return get_engine()
    if name == "async_session_factory":
        return get_async_session_factory()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    # Asegurar que todos los modelos del dominio estén registrados en Base.metadata
    from app.domain.auth import models as _auth_models  # noqa: F401
    from app.domain.clinica import models as _clinica_models  # noqa: F401
    from app.domain.personas import models as _personas_models  # noqa: F401
    from app.domain.turnos import models as _turnos_models  # noqa: F401

    async with get_engine().begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    if _engine is not None:
        await _engine.dispose()
