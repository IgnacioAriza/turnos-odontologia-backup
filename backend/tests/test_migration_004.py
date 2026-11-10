"""Tests para la migración 004 de Alembic (catálogo C-04)."""

import pytest
from sqlalchemy import text

from app.core.config import settings

pg_only = pytest.mark.skipif(
    "sqlite" in settings.database_url,
    reason="Requires PostgreSQL for information_schema/pg_catalog queries",
)


@pg_only
@pytest.mark.asyncio
async def test_tables_exist(db_session):
    """Las tres tablas del catálogo deben existir."""
    result = await db_session.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    )
    tables = {row[0] for row in result.fetchall()}

    assert {"tipos_practica", "aranceles", "auditorias_sena"} <= tables


@pg_only
@pytest.mark.asyncio
async def test_columns_exist(db_session):
    """Columnas clave de tipos_practica y aranceles."""
    result = await db_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'tipos_practica'"
        )
    )
    tipo_cols = {row[0] for row in result.fetchall()}
    assert {
        "id",
        "clinic_id",
        "nombre",
        "duracion_min",
        "precio_base",
        "sena_pct",
        "activa",
        "is_active",
        "created_at",
        "updated_at",
    } <= tipo_cols

    result = await db_session.execute(
        text("SELECT column_name FROM information_schema.columns " "WHERE table_name = 'aranceles'")
    )
    arancel_cols = {row[0] for row in result.fetchall()}
    assert {"id", "tipo_practica_id", "precio", "sena_pct", "vigente_desde"} <= arancel_cols


@pg_only
@pytest.mark.asyncio
async def test_check_constraints_exist(db_session):
    """Deben existir los CHECKs de duración, precio y rango de seña."""
    result = await db_session.execute(
        text(
            "SELECT conrelid::regclass::text AS tabla, pg_get_constraintdef(oid) AS definicion "
            "FROM pg_constraint WHERE contype = 'c' "
            "AND conrelid::regclass::text IN ('tipos_practica', 'aranceles')"
        )
    )
    checks = {(row[0], row[1]) for row in result.fetchall()}

    def tiene(tabla: str, fragmento: str) -> bool:
        return any(t == tabla and fragmento in d for t, d in checks)

    assert tiene("tipos_practica", "duracion_min")
    assert tiene("tipos_practica", "precio_base")
    assert tiene("tipos_practica", "sena_pct")
    assert tiene("aranceles", "precio")
    assert tiene("aranceles", "sena_pct")


@pg_only
@pytest.mark.asyncio
async def test_unique_arancel_por_practica(db_session):
    """Debe existir UNIQUE (tipo_practica_id) en aranceles."""
    result = await db_session.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE contype = 'u' AND conrelid = 'aranceles'::regclass"
        )
    )
    definiciones = " ".join(row[0] for row in result.fetchall())

    assert "tipo_practica_id" in definiciones


@pg_only
@pytest.mark.asyncio
async def test_indexes_exist(db_session):
    """Deben existir los índices por clínica y el compuesto de auditoría."""
    result = await db_session.execute(
        text(
            "SELECT tablename, indexname FROM pg_indexes "
            "WHERE tablename IN ('tipos_practica', 'aranceles', 'auditorias_sena')"
        )
    )
    indexes = {(row[0], row[1]) for row in result.fetchall()}

    assert ("tipos_practica", "ix_tipos_practica_clinic_id") in indexes
    assert ("tipos_practica", "ix_tipos_practica_clinic_id_activa") in indexes
    assert ("aranceles", "ix_aranceles_tipo_practica_id") in indexes
    assert ("auditorias_sena", "ix_auditorias_sena_clinic_tipo_created") in indexes
