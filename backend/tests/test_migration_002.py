"""Tests para la migración 002 de Alembic (esquema inicial C-02)."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.skipif(
    "sqlite" in __import__("app.core.config", fromlist=["settings"]).settings.database_url,
    reason="Requires PostgreSQL for information_schema queries",
)
@pytest.mark.asyncio
async def test_tables_exist(db_session: AsyncSession):
    """Todas las tablas de la migración 002 deben existir."""
    result = await db_session.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    )
    tables = {row[0] for row in result.fetchall()}

    expected = {"clinic", "users", "pacientes", "sillones", "bloqueos"}
    for table in expected:
        assert table in tables, f"Tabla {table} no encontrada"


@pytest.mark.skipif(
    "sqlite" in __import__("app.core.config", fromlist=["settings"]).settings.database_url,
    reason="Requires PostgreSQL for information_schema queries",
)
@pytest.mark.asyncio
async def test_columns_exist(db_session: AsyncSession):
    """Columnas clave deben existir en cada tabla."""
    # clinic
    result = await db_session.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name = 'clinic'")
    )
    clinic_cols = {row[0] for row in result.fetchall()}
    assert {"id", "nombre", "timezone", "is_active", "created_at", "updated_at"} <= clinic_cols

    # users
    result = await db_session.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name = 'users'")
    )
    users_cols = {row[0] for row in result.fetchall()}
    assert {"id", "clinic_id", "email", "password_hash", "rol", "activo"} <= users_cols

    # pacientes
    result = await db_session.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name = 'pacientes'")
    )
    pacientes_cols = {row[0] for row in result.fetchall()}
    assert {"id", "clinic_id", "nombre", "telefono", "dni"} <= pacientes_cols


@pytest.mark.skipif(
    "sqlite" in __import__("app.core.config", fromlist=["settings"]).settings.database_url,
    reason="Requires PostgreSQL for pg_constraint queries",
)
@pytest.mark.asyncio
async def test_unique_constraint_email_per_clinic(db_session: AsyncSession):
    """Debe existir constraint UNIQUE (clinic_id, email) en users."""
    result = await db_session.execute(
        text(
            "SELECT conname FROM pg_constraint WHERE conrelid = 'users'::regclass AND contype = 'u'"
        )
    )
    constraints = {row[0] for row in result.fetchall()}
    assert any("clinic_id" in c and "email" in c for c in constraints), (
        "Falta constraint UNIQUE (clinic_id, email) en users"
    )


@pytest.mark.skipif(
    "sqlite" in __import__("app.core.config", fromlist=["settings"]).settings.database_url,
    reason="Requires PostgreSQL for pg_indexes queries",
)
@pytest.mark.asyncio
async def test_indexes_exist(db_session: AsyncSession):
    """Debe existir índice compuesto (clinic_id, telefono) y (clinic_id, dni) en pacientes."""
    result = await db_session.execute(
        text("SELECT indexname FROM pg_indexes WHERE tablename = 'pacientes'")
    )
    indexes = {row[0] for row in result.fetchall()}
    assert any("clinic_id" in i and "telefono" in i for i in indexes), (
        "Falta índice compuesto (clinic_id, telefono) en pacientes"
    )
    assert any("clinic_id" in i and "dni" in i for i in indexes), (
        "Falta índice compuesto (clinic_id, dni) en pacientes"
    )
