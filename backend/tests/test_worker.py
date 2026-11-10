"""Tests del barrido de turnos vencidos en el worker (C-05)."""

from datetime import UTC, datetime, time, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.turnos.models import Turno
from app.infrastructure.queue import worker
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


async def _escenario(db_session: AsyncSession) -> dict[str, object]:
    clinic = await crear_clinica(db_session)
    return {
        "clinic": clinic,
        "practica": await crear_practica(db_session, clinic),
        "sillon": await crear_sillon(db_session, clinic),
        "odonto": await crear_odontologo(db_session, clinic),
        "paciente": await crear_paciente(db_session, clinic),
    }


@pytest.mark.asyncio
async def test_barrido_expira_pendientes_vencidos(db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    ahora = datetime.now(UTC)
    await crear_turno(
        db_session,
        clinic=base["clinic"],  # type: ignore[arg-type]
        paciente=base["paciente"],  # type: ignore[arg-type]
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=local(LUNES, time(10, 0)),
        estado="pendiente_sena",
        expira_at=ahora - timedelta(minutes=5),
    )

    cantidad = await worker.barrido_una_vez(now=ahora, session=db_session)

    assert cantidad == 1
    guardados = list((await db_session.execute(select(Turno))).scalars().all())
    assert [turno.estado for turno in guardados] == ["cancelado"]


@pytest.mark.asyncio
async def test_barrido_sin_vencidos_no_cambia_nada(db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    ahora = datetime.now(UTC)
    await crear_turno(
        db_session,
        clinic=base["clinic"],  # type: ignore[arg-type]
        paciente=base["paciente"],  # type: ignore[arg-type]
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=local(LUNES, time(11, 0)),
        estado="confirmado",
    )

    assert await worker.barrido_una_vez(now=ahora, session=db_session) == 0


@pytest.mark.asyncio
async def test_barrido_usa_sesion_propia_y_commitea(db_session: AsyncSession) -> None:
    """Sin `session` explícita el barrido abre su propia sesión y persiste."""
    base = await _escenario(db_session)
    ahora = datetime.now(UTC)
    turno = await crear_turno(
        db_session,
        clinic=base["clinic"],  # type: ignore[arg-type]
        paciente=base["paciente"],  # type: ignore[arg-type]
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=local(LUNES, time(12, 0)),
        estado="pendiente_sena",
        expira_at=ahora - timedelta(minutes=1),
    )
    await db_session.commit()

    assert await worker.barrido_una_vez(now=ahora) == 1

    await db_session.refresh(turno)
    assert turno.estado == "cancelado"
