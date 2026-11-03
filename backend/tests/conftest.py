"""Configuración de tests para el backend de turnos-odontologia."""

import asyncio
import os
from typing import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Configurar variable de entorno ANTES de importar cualquier cosa de la app
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"

from app.infrastructure.db.base import Base, get_engine

# Crear engine async de SQLite en memoria para tests
test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
)

TestAsyncSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Proporciona una sesión de base de datos de prueba (SQLite en memoria)."""
    # Crear todas las tablas en el engine de test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # También crear tablas en el engine de la app (para tests que usan TestClient)
    app_engine = get_engine()
    async with app_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestAsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

    # Limpiar tablas
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    async with app_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
