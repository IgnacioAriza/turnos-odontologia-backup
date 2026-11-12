"""Tests de reprogramación de turnos (C-06, tareas 4.1–4.6)."""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, UnprocessableError
from app.domain.clinica.models import Clinic, TipoPractica
from app.domain.turnos import service
from app.domain.turnos.models import Turno
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


def _naive_utc(value: datetime) -> datetime:
    """SQLite devuelve naive; normalizar para comparar instantes."""
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


async def _escenario(
    db: AsyncSession,
    *,
    estado: str = "confirmado",
    monto_sena: Decimal = Decimal("2000.00"),
    hora: time = time(10, 0),
    expira_at: datetime | None = None,
    reprogramaciones_count: int = 0,
    con_horario: bool = True,
) -> dict[str, Any]:
    clinic: Clinic = await crear_clinica(db)
    practica: TipoPractica = await crear_practica(db, clinic, duracion_min=30)
    sillon = await crear_sillon(db, clinic)
    odonto = await crear_odontologo(db, clinic)
    paciente = await crear_paciente(db, clinic)
    if con_horario:
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
        expira_at=expira_at,
        reprogramaciones_count=reprogramaciones_count,
        manage_token="token-original",
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
async def test_primera_reprogramacion_muta_el_turno_en_el_lugar(
    db_session: AsyncSession,
) -> None:
    expira = datetime.now(UTC) + timedelta(minutes=20)
    base = await _escenario(
        db_session, estado="pendiente_sena", expira_at=expira, reprogramaciones_count=0
    )
    recordatorio = RecordatorioFake()
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    turno = await service.reprogramar_turno(
        db_session,
        turno=base["turno"],
        clinic=base["clinic"],
        nuevo_inicio=local(LUNES, time(11, 0)),
        now=now,
        recordatorio=recordatorio,
    )

    assert turno.id == base["turno"].id
    assert turno.inicio == local(LUNES, time(11, 0)).astimezone(UTC)
    assert turno.fin == local(LUNES, time(11, 30)).astimezone(UTC)
    assert turno.monto_sena == Decimal("2000.00")
    assert turno.reprogramaciones_count == 1
    assert turno.manage_token == "token-original"
    assert turno.estado == "pendiente_sena"
    assert turno.expira_at is not None
    assert turno.sena_perdida is False
    assert recordatorio.reprogramados == [(turno.id, local(LUNES, time(11, 0)).astimezone(UTC))]


@pytest.mark.asyncio
async def test_primera_reprogramacion_de_confirmado_no_tiene_expiracion(
    db_session: AsyncSession,
) -> None:
    base = await _escenario(db_session, estado="confirmado")
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    turno = await service.reprogramar_turno(
        db_session,
        turno=base["turno"],
        clinic=base["clinic"],
        nuevo_inicio=local(LUNES, time(12, 0)),
        now=now,
    )

    assert turno.estado == "confirmado"
    assert turno.expira_at is None
    assert turno.reprogramaciones_count == 1


@pytest.mark.asyncio
async def test_reprogramar_a_horario_ocupado_da_solape_y_no_cambia_nada(
    db_session: AsyncSession,
) -> None:
    base = await _escenario(db_session)
    otro_paciente = await crear_paciente(db_session, base["clinic"], telefono="+5491199999999")
    await crear_turno(
        db_session,
        clinic=base["clinic"],
        paciente=otro_paciente,
        sillon=base["sillon"],
        odontologo=base["odonto"],
        practica=base["practica"],
        inicio=local(LUNES, time(11, 0)),
        estado="confirmado",
    )
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    with pytest.raises(ConflictError) as exc:
        await service.reprogramar_turno(
            db_session,
            turno=base["turno"],
            clinic=base["clinic"],
            nuevo_inicio=local(LUNES, time(11, 0)),
            now=now,
        )

    assert exc.value.status_code == 409
    assert exc.value.code == "solape"
    await db_session.refresh(base["turno"])
    assert _naive_utc(base["turno"].inicio) == _naive_utc(local(LUNES, time(10, 0)))
    assert base["turno"].reprogramaciones_count == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("hora", [time(10, 15), time(21, 0)])
async def test_reprogramar_a_slot_invalido_da_422(db_session: AsyncSession, hora: time) -> None:
    base = await _escenario(db_session)
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    with pytest.raises(UnprocessableError) as exc:
        await service.reprogramar_turno(
            db_session,
            turno=base["turno"],
            clinic=base["clinic"],
            nuevo_inicio=local(LUNES, hora),
            now=now,
        )

    assert exc.value.status_code == 422
    assert exc.value.code == "slot_invalido"


@pytest.mark.asyncio
async def test_reprogramar_sin_franja_configurada_da_slot_invalido(
    db_session: AsyncSession,
) -> None:
    base = await _escenario(db_session, con_horario=False)
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    with pytest.raises(UnprocessableError) as exc:
        await service.reprogramar_turno(
            db_session,
            turno=base["turno"],
            clinic=base["clinic"],
            nuevo_inicio=local(LUNES, time(11, 0)),
            now=now,
        )

    assert exc.value.code == "slot_invalido"


@pytest.mark.asyncio
async def test_reprogramar_fuera_de_ventana_requiere_confirmacion(
    db_session: AsyncSession,
) -> None:
    """El horario nuevo a menos de 12 horas también exige confirmación."""
    base = await _escenario(db_session)

    with pytest.raises(ConflictError) as exc:
        await service.reprogramar_turno(
            db_session,
            turno=base["turno"],
            clinic=base["clinic"],
            nuevo_inicio=local(LUNES, time(11, 0)),
            now=local(LUNES, time(11, 0)) - timedelta(hours=5),
        )

    assert exc.value.code == "requiere_confirmacion"
    assert exc.value.extra == {"perdida_sena": True}
    await db_session.refresh(base["turno"])
    assert _naive_utc(base["turno"].inicio) == _naive_utc(local(LUNES, time(10, 0)))


@pytest.mark.asyncio
async def test_reprogramar_fuera_de_ventana_confirmado_marca_sena_perdida(
    db_session: AsyncSession,
) -> None:
    base = await _escenario(db_session)
    recordatorio = RecordatorioFake()
    now = local(LUNES, time(10, 0)) - timedelta(hours=5)
    nuevo = local(LUNES, time(12, 0))

    turno = await service.reprogramar_turno(
        db_session,
        turno=base["turno"],
        clinic=base["clinic"],
        nuevo_inicio=nuevo,
        confirmar_perdida_sena=True,
        now=now,
        recordatorio=recordatorio,
    )

    assert turno.id == base["turno"].id
    assert turno.inicio == nuevo.astimezone(UTC)
    assert turno.sena_perdida is True
    assert turno.monto_sena == Decimal("2000.00")
    assert recordatorio.reprogramados == [(turno.id, nuevo.astimezone(UTC))]


@pytest.mark.asyncio
async def test_segunda_reprogramacion_sin_confirmar_no_crea_nada(
    db_session: AsyncSession,
) -> None:
    base = await _escenario(db_session, reprogramaciones_count=1)
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    with pytest.raises(ConflictError) as exc:
        await service.reprogramar_turno(
            db_session,
            turno=base["turno"],
            clinic=base["clinic"],
            nuevo_inicio=local(LUNES, time(11, 0)),
            now=now,
        )

    assert exc.value.status_code == 409
    assert exc.value.code == "requiere_nueva_sena"
    turnos = list((await db_session.execute(select(Turno))).scalars().all())
    assert len(turnos) == 1
    await db_session.refresh(base["turno"])
    assert base["turno"].estado == "confirmado"


@pytest.mark.asyncio
async def test_segunda_reprogramacion_confirmada_crea_turno_nuevo(
    db_session: AsyncSession,
) -> None:
    base = await _escenario(db_session, reprogramaciones_count=1)
    recordatorio = RecordatorioFake()
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    nuevo = await service.reprogramar_turno(
        db_session,
        turno=base["turno"],
        clinic=base["clinic"],
        nuevo_inicio=local(LUNES, time(11, 0)),
        confirmar_perdida_sena=True,
        now=now,
        recordatorio=recordatorio,
    )

    await db_session.refresh(base["turno"])
    assert base["turno"].estado == "cancelado"
    assert base["turno"].sena_perdida is True

    assert nuevo.id != base["turno"].id
    assert nuevo.estado == "pendiente_sena"
    assert nuevo.reprogramado_de_id == base["turno"].id
    assert nuevo.reprogramaciones_count == 1
    assert nuevo.manage_token is not None
    assert nuevo.manage_token != "token-original"
    assert nuevo.monto_sena == Decimal("2000.00")
    assert nuevo.expira_at is not None
    assert nuevo.expira_at > now
    assert nuevo.inicio == local(LUNES, time(11, 0)).astimezone(UTC)
    assert recordatorio.cancelados == [base["turno"].id]
    assert recordatorio.reprogramados == [(nuevo.id, nuevo.inicio)]


@pytest.mark.asyncio
async def test_segunda_reprogramacion_recalcula_la_sena(db_session: AsyncSession) -> None:
    clinic = await crear_clinica(db_session)
    practica = await crear_practica(
        db_session, clinic, duracion_min=30, precio=Decimal("15000.00"), sena_pct=30
    )
    sillon = await crear_sillon(db_session, clinic)
    odonto = await crear_odontologo(db_session, clinic)
    paciente = await crear_paciente(db_session, clinic)
    await crear_horario(db_session, clinic, dia_semana=0, desde=time(8, 0), hasta=time(20, 0))
    turno = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente,
        sillon=sillon,
        odontologo=odonto,
        practica=practica,
        inicio=local(LUNES, time(10, 0)),
        estado="confirmado",
        monto_sena=Decimal("1000.00"),
        reprogramaciones_count=1,
    )
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    nuevo = await service.reprogramar_turno(
        db_session,
        turno=turno,
        clinic=clinic,
        nuevo_inicio=local(LUNES, time(11, 0)),
        confirmar_perdida_sena=True,
        now=now,
    )

    assert nuevo.monto_sena == Decimal("4500.00")


@pytest.mark.asyncio
async def test_horario_liberado_por_la_segunda_reprogramacion_es_re_reservable(
    db_session: AsyncSession,
) -> None:
    base = await _escenario(db_session, reprogramaciones_count=1)
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    nuevo = await service.reprogramar_turno(
        db_session,
        turno=base["turno"],
        clinic=base["clinic"],
        nuevo_inicio=local(LUNES, time(11, 0)),
        confirmar_perdida_sena=True,
        now=now,
    )

    liberado = await service.crear_turno_publico(
        db_session,
        nombre="Tercero",
        telefono="+5491177777777",
        dni=None,
        practica_id=base["practica"].id,
        inicio=local(LUNES, time(10, 0)),
        now=now,
    )
    assert liberado.inicio == local(LUNES, time(10, 0)).astimezone(UTC)
    assert liberado.manage_token != nuevo.manage_token


@pytest.mark.asyncio
async def test_turno_nuevo_de_la_segunda_reprogramacion_expira(db_session: AsyncSession) -> None:
    base = await _escenario(db_session, reprogramaciones_count=1)
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    nuevo = await service.reprogramar_turno(
        db_session,
        turno=base["turno"],
        clinic=base["clinic"],
        nuevo_inicio=local(LUNES, time(11, 0)),
        confirmar_perdida_sena=True,
        now=now,
    )
    assert nuevo.expira_at is not None

    expirados = await service.expirar_pendientes(db_session, now=nuevo.expira_at)
    await db_session.commit()

    assert expirados == 1
    await db_session.refresh(nuevo)
    assert nuevo.estado == "cancelado"


@pytest.mark.asyncio
@pytest.mark.parametrize("estado", ["cancelado", "completado", "ausente"])
async def test_reprogramar_estado_final_no_es_gestionable(
    db_session: AsyncSession, estado: str
) -> None:
    base = await _escenario(db_session, estado=estado)
    now = local(LUNES, time(10, 0)) - timedelta(hours=30)

    with pytest.raises(ConflictError) as exc:
        await service.reprogramar_turno(
            db_session,
            turno=base["turno"],
            clinic=base["clinic"],
            nuevo_inicio=local(LUNES, time(11, 0)),
            confirmar_perdida_sena=True,
            now=now,
        )

    assert exc.value.code == "estado_no_gestionable"
