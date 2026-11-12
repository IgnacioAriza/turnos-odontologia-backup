"""Tests de la migración 006 y del modelo de gestión de turnos (C-06)."""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from tests.turnos_factories import (
    LUNES,
    crear_clinica,
    crear_odontologo,
    crear_paciente,
    crear_practica,
    crear_sillon,
    crear_turno,
    local,
)

pg_only = pytest.mark.skipif(
    "sqlite" in settings.database_url,
    reason="Requires PostgreSQL for information_schema/pg_catalog queries",
)


@pg_only
@pytest.mark.asyncio
async def test_columnas_de_gestion_existen(db_session: AsyncSession):
    """`sena_perdida` NOT NULL default false y `reprogramado_de_id` nullable."""
    result = await db_session.execute(
        text(
            "SELECT column_name, is_nullable, column_default "
            "FROM information_schema.columns WHERE table_name = 'turnos'"
        )
    )
    columnas = {row[0]: (row[1], row[2]) for row in result.fetchall()}

    assert columnas["sena_perdida"][0] == "NO"
    assert columnas["sena_perdida"][1] is not None
    assert "false" in str(columnas["sena_perdida"][1]).lower()
    assert columnas["reprogramado_de_id"][0] == "YES"


@pg_only
@pytest.mark.asyncio
async def test_fk_reprogramado_de_apunta_a_turnos(db_session: AsyncSession):
    """`reprogramado_de_id` tiene FK a `turnos.id` con ON DELETE SET NULL."""
    result = await db_session.execute(
        text(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint "
            "WHERE contype = 'f' AND conrelid = 'turnos'::regclass"
        )
    )
    definiciones = [row[0] for row in result.fetchall()]
    fk = next((d for d in definiciones if "reprogramado_de_id" in d), None)

    assert fk is not None
    assert "REFERENCES turnos(id)" in fk
    assert "SET NULL" in fk


@pg_only
@pytest.mark.asyncio
async def test_indice_reprogramado_de_existe(db_session: AsyncSession):
    result = await db_session.execute(
        text(
            "SELECT indexname FROM pg_indexes WHERE tablename = 'turnos' "
            "AND indexname = 'ix_turnos_reprogramado_de_id'"
        )
    )
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_modelo_turno_tiene_campos_de_gestion(db_session: AsyncSession) -> None:
    """El modelo mapea `sena_perdida=False` por defecto y la cadena de reprogramación."""
    clinic = await crear_clinica(db_session)
    practica = await crear_practica(db_session, clinic)
    sillon = await crear_sillon(db_session, clinic)
    odonto = await crear_odontologo(db_session, clinic)
    paciente = await crear_paciente(db_session, clinic)

    original = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente,
        sillon=sillon,
        odontologo=odonto,
        practica=practica,
        inicio=local(LUNES, time(10, 0)),
        estado="cancelado",
        monto_sena=Decimal("2000.00"),
    )
    await db_session.refresh(original)
    assert original.sena_perdida is False
    assert original.reprogramado_de_id is None

    nuevo = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente,
        sillon=sillon,
        odontologo=odonto,
        practica=practica,
        inicio=local(LUNES, time(11, 0)),
        estado="pendiente_sena",
        expira_at=datetime.now(UTC) + timedelta(minutes=30),
        monto_sena=Decimal("2000.00"),
    )
    nuevo.reprogramado_de_id = original.id
    await db_session.flush()
    await db_session.refresh(nuevo)

    assert nuevo.reprogramado_de_id == original.id
    assert nuevo.monto_sena == Decimal("2000.00")
