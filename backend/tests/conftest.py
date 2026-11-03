"""Configuración de tests para el backend de turnos-odontologia."""

import os
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

# Configurar variable de entorno ANTES de importar cualquier cosa de la app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

from app.infrastructure.db.base import Base, get_async_session_factory, get_engine

# Usar el MISMO engine que la app usa (get_engine está cacheado)
test_engine = get_engine()
TestAsyncSessionLocal = get_async_session_factory()


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Proporciona una sesión de base de datos de prueba (SQLite archivo compartido)."""
    # Crear todas las tablas en el engine compartido
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

    # Limpiar tablas
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
