"""Tests para la migración 005 de Alembic (motor de turnos C-05)."""

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
    """Las tablas del motor de turnos deben existir."""
    result = await db_session.execute(
        text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
    )
    tables = {row[0] for row in result.fetchall()}

    assert {"turnos", "horarios_atencion"} <= tables


@pg_only
@pytest.mark.asyncio
async def test_columns_exist(db_session):
    """Columnas clave de turnos, horarios y ajustes de pacientes."""
    result = await db_session.execute(
        text("SELECT column_name FROM information_schema.columns WHERE table_name = 'turnos'")
    )
    turno_cols = {row[0] for row in result.fetchall()}
    assert {
        "id",
        "clinic_id",
        "paciente_id",
        "sillon_id",
        "odontologo_id",
        "tipo_practica_id",
        "inicio",
        "fin",
        "estado",
        "manage_token",
        "reprogramaciones_count",
        "monto_sena",
        "expira_at",
        "is_active",
        "created_at",
        "updated_at",
    } <= turno_cols

    result = await db_session.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'horarios_atencion'"
        )
    )
    horario_cols = {row[0] for row in result.fetchall()}
    assert {
        "id",
        "clinic_id",
        "dia_semana",
        "hora_desde",
        "hora_hasta",
        "activo",
    } <= horario_cols

    result = await db_session.execute(
        text(
            "SELECT column_name, is_nullable FROM information_schema.columns "
            "WHERE table_name = 'pacientes'"
        )
    )
    paciente_cols = {row[0]: row[1] for row in result.fetchall()}
    assert paciente_cols["dni"] == "YES"
    assert "bloqueado_hasta" in paciente_cols
    assert "faltas_count" in paciente_cols


@pg_only
@pytest.mark.asyncio
async def test_check_constraints_exist(db_session):
    """Deben existir los CHECKs de turnos y horarios."""
    result = await db_session.execute(
        text(
            "SELECT conrelid::regclass::text AS tabla, pg_get_constraintdef(oid) AS definicion "
            "FROM pg_constraint WHERE contype = 'c' "
            "AND conrelid::regclass::text IN ('turnos', 'horarios_atencion')"
        )
    )
    checks = {(row[0], row[1]) for row in result.fetchall()}

    def tiene(tabla: str, fragmento: str) -> bool:
        return any(t == tabla and fragmento in d for t, d in checks)

    assert tiene("turnos", "fin > inicio")
    assert tiene("turnos", "monto_sena")
    assert tiene("turnos", "estado")
    assert tiene("horarios_atencion", "hora_hasta > hora_desde")
    assert tiene("horarios_atencion", "dia_semana")


@pg_only
@pytest.mark.asyncio
async def test_unique_constraints_exist(db_session):
    """UNIQUE de manage_token, horario y teléfono por clínica."""
    result = await db_session.execute(
        text(
            "SELECT conrelid::regclass::text AS tabla, pg_get_constraintdef(oid) AS definicion "
            "FROM pg_constraint WHERE contype = 'u' "
            "AND conrelid::regclass::text IN ('turnos', 'horarios_atencion', 'pacientes')"
        )
    )
    uniques = {(row[0], row[1]) for row in result.fetchall()}

    def tiene(tabla: str, fragmento: str) -> bool:
        return any(t == tabla and fragmento in d for t, d in uniques)

    assert tiene("turnos", "manage_token")
    assert tiene("horarios_atencion", "clinic_id, dia_semana, hora_desde")
    assert tiene("pacientes", "clinic_id, telefono")


@pg_only
@pytest.mark.asyncio
async def test_exclude_constraints_exist(db_session):
    """Los dos EXCLUDE anti-solape deben existir y usar tstzrange."""
    result = await db_session.execute(
        text(
            "SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE contype = 'x' AND conrelid = 'turnos'::regclass"
        )
    )
    rows = {row[0]: row[1] for row in result.fetchall()}

    assert "ex_turnos_sillon_solape" in rows
    assert "ex_turnos_odontologo_solape" in rows
    assert "tstzrange" in rows["ex_turnos_sillon_solape"]
    assert "tstzrange" in rows["ex_turnos_odontologo_solape"]


@pg_only
@pytest.mark.asyncio
async def test_indexes_exist(db_session):
    """Deben existir los índices por recurso, fecha y barrido."""
    result = await db_session.execute(
        text(
            "SELECT tablename, indexname FROM pg_indexes "
            "WHERE tablename IN ('turnos', 'horarios_atencion')"
        )
    )
    indexes = {(row[0], row[1]) for row in result.fetchall()}

    assert ("turnos", "ix_turnos_clinic_inicio") in indexes
    assert ("turnos", "ix_turnos_sillon_inicio") in indexes
    assert ("turnos", "ix_turnos_odontologo_inicio") in indexes
    assert ("turnos", "ix_turnos_paciente_inicio") in indexes
    assert ("turnos", "ix_turnos_estado_expira") in indexes
    assert ("horarios_atencion", "ix_horarios_atencion_clinic_id") in indexes
