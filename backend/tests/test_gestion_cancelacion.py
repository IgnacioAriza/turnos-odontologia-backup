"""Tests de cancelación de turnos con ventana de 12 horas (C-06, tareas 3.3 y 3.5)."""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.domain.clinica.models import Clinic, TipoPractica
from app.domain.turnos import service
from tests.turnos_factories import (
    LUNES,
    crear_clinica,
    crear_horario,
    crear_odontologo,
    crear_paciente,
    crear_practica,
    crear_sillon,
    crear_turno,
    local,
)


class RecordatorioFake:
    def __init__(self) -> None:
        self.cancelados: list[UUID] = []
        self.reprogramados: list[tuple[UUID, datetime]] = []

    async def cancelar(self, turno_id: UUID) -> None:
        self.cancelados.append(turno_id)

    async def reprogramar(self, turno_id: UUID, inicio: datetime) -> None:
        self.reprogramados.append((turno_id, inicio))


async def _escenario(
    db: AsyncSession,
    *,
    estado: str = "confirmado",
    monto_sena: Decimal = Decimal("2000.00"),
    hora: time = time(10, 0),
    duracion_min: int = 30,
) -> dict[str, Any]:
    clinic: Clinic = await crear_clinica(db)
    practica: TipoPractica = await crear_practica(db, clinic, duracion_min=duracion_min)
    sillon = await crear_sillon(db, clinic)
    odonto = await crear_odontologo(db, clinic)
    paciente = await crear_paciente(db, clinic)
    await crear_horario(db, clinic, dia_semana=0, desde=time(8, 0), hasta=time(20, 0))
    turno = await crear_turno(
        db,
        clinic=clinic,
        paciente=paciente,
        sillon=sillon,
        odontologo=odonto,
        practica=practica,
        inicio=local(LUNES, hora),
        estado=estado,
        monto_sena=monto_sena,
        duracion_min=duracion_min,
    )
    return {
        "clinic": clinic,
        "practica": practica,
        "sillon": sillon,
        "odonto": odonto,
        "paciente": paciente,
        "turno": turno,
    }


@pytest.mark.asyncio
async def test_cancelar_dentro_de_ventana_no_toca_la_sena(db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    recordatorio = RecordatorioFake()
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    turno = await service.cancelar_turno(
        db_session,
        turno=base["turno"],
        clinic=base["clinic"],
        now=now,
        recordatorio=recordatorio,
    )

    assert turno.estado == "cancelado"
    assert turno.sena_perdida is False
    await db_session.refresh(turno)
    assert turno.estado == "cancelado"
    assert recordatorio.cancelados == [turno.id]


@pytest.mark.asyncio
async def test_cancelar_pendiente_sena_libera_sin_perder_sena(db_session: AsyncSession) -> None:
    base = await _escenario(db_session, estado="pendiente_sena")
    now = local(LUNES, time(10, 0)) - timedelta(hours=5)

    turno = await service.cancelar_turno(
        db_session, turno=base["turno"], clinic=base["clinic"], now=now
    )

    assert turno.estado == "cancelado"
    assert turno.sena_perdida is False


@pytest.mark.asyncio
@pytest.mark.parametrize("estado", ["cancelado", "completado", "ausente"])
async def test_estado_final_no_es_gestionable(db_session: AsyncSession, estado: str) -> None:
    base = await _escenario(db_session, estado=estado)
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    with pytest.raises(ConflictError) as exc:
        await service.cancelar_turno(
            db_session,
            turno=base["turno"],
            clinic=base["clinic"],
            now=now,
            confirmar_perdida_sena=True,
        )

    assert exc.value.status_code == 409
    assert exc.value.code == "estado_no_gestionable"
    await db_session.refresh(base["turno"])
    assert base["turno"].estado == estado


@pytest.mark.asyncio
async def test_cancelacion_tardia_sin_confirmar_no_cambia_nada(db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    recordatorio = RecordatorioFake()
    now = local(LUNES, time(10, 0)) - timedelta(hours=5)

    with pytest.raises(ConflictError) as exc:
        await service.cancelar_turno(
            db_session,
            turno=base["turno"],
            clinic=base["clinic"],
            now=now,
            recordatorio=recordatorio,
        )

    assert exc.value.status_code == 409
    assert exc.value.code == "requiere_confirmacion"
    assert exc.value.extra == {"perdida_sena": True}
    await db_session.refresh(base["turno"])
    assert base["turno"].estado == "confirmado"
    assert base["turno"].sena_perdida is False
    assert recordatorio.cancelados == []


@pytest.mark.asyncio
async def test_cancelacion_tardia_confirmada_marca_sena_perdida(
    db_session: AsyncSession,
) -> None:
    base = await _escenario(db_session)
    now = local(LUNES, time(10, 0)) - timedelta(hours=5)

    turno = await service.cancelar_turno(
        db_session,
        turno=base["turno"],
        clinic=base["clinic"],
        now=now,
        confirmar_perdida_sena=True,
    )

    await db_session.refresh(turno)
    assert turno.estado == "cancelado"
    assert turno.sena_perdida is True


@pytest.mark.asyncio
async def test_cancelacion_tardia_sin_pago_aprobado_no_marca_perdida(
    db_session: AsyncSession,
) -> None:
    """Sin seña aprobada no hay nada que perder: se cancela sin confirmar."""
    base = await _escenario(db_session, estado="pendiente_sena", monto_sena=Decimal("0.00"))
    now = local(LUNES, time(10, 0)) - timedelta(hours=5)

    turno = await service.cancelar_turno(
        db_session, turno=base["turno"], clinic=base["clinic"], now=now
    )

    await db_session.refresh(turno)
    assert turno.estado == "cancelado"
    assert turno.sena_perdida is False


@pytest.mark.asyncio
async def test_cancelar_libera_el_horario_para_re_reservar(db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    await service.cancelar_turno(db_session, turno=base["turno"], clinic=base["clinic"], now=now)

    dia = await service.obtener_slots(
        db_session, practica_id=base["practica"].id, fecha=LUNES, now=now
    )
    assert local(LUNES, time(10, 0)).astimezone(UTC) in [slot.inicio for slot in dia.slots]

    nuevo = await service.crear_turno_publico(
        db_session,
        nombre="Otro Paciente",
        telefono="+5491100000000",
        dni=None,
        practica_id=base["practica"].id,
        inicio=local(LUNES, time(10, 0)),
        now=now,
    )
    assert nuevo.id != base["turno"].id
    assert nuevo.estado == "pendiente_sena"


@pytest.mark.asyncio
async def test_cancelar_registra_dominio_sin_token(
    db_session: AsyncSession, capsys: pytest.CaptureFixture[str]
) -> None:
    base = await _escenario(db_session)
    usuario_id = uuid4()
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    await service.cancelar_turno(
        db_session,
        turno=base["turno"],
        clinic=base["clinic"],
        now=now,
        motivo="Paciente avisó por teléfono",
        usuario_id=usuario_id,
    )

    salida = capsys.readouterr().out
    assert "turno_cancelado" in salida
    assert str(base["turno"].id) in salida
    assert str(usuario_id) in salida
    assert "manage_token" not in salida
