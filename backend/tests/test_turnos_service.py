"""Tests del servicio del motor de turnos (C-05)."""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.domain.personas.models import Paciente
from app.domain.personas.repository import PacienteRepository
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


@pytest.mark.asyncio
async def test_get_or_create_paciente_nuevo(db_session: AsyncSession) -> None:
    clinic = await crear_clinica(db_session)
    repo = PacienteRepository(db_session)

    paciente = await repo.get_or_create_by_telefono(
        clinic_id=clinic.id, telefono="+5491112345678", nombre="Ana", dni="30111222"
    )

    assert paciente.id is not None
    assert paciente.nombre == "Ana"
    assert paciente.dni == "30111222"
    assert paciente.clinic_id == clinic.id


@pytest.mark.asyncio
async def test_get_or_create_paciente_existente_no_duplica(db_session: AsyncSession) -> None:
    clinic = await crear_clinica(db_session)
    creado = await crear_paciente(db_session, clinic, telefono="+5491112345678")
    repo = PacienteRepository(db_session)

    reutilizado = await repo.get_or_create_by_telefono(
        clinic_id=clinic.id, telefono="+5491112345678", nombre="Otro nombre"
    )

    assert reutilizado.id == creado.id
    result = await db_session.execute(select(Paciente).where(Paciente.telefono == "+5491112345678"))
    assert len(list(result.scalars().all())) == 1


@pytest.mark.asyncio
async def test_get_or_create_mismo_telefono_en_otra_clinica(db_session: AsyncSession) -> None:
    clinic_a = await crear_clinica(db_session)
    clinic_b = await crear_clinica(db_session)
    repo = PacienteRepository(db_session)

    a = await repo.get_or_create_by_telefono(
        clinic_id=clinic_a.id, telefono="+5491112345678", nombre="A"
    )
    b = await repo.get_or_create_by_telefono(
        clinic_id=clinic_b.id, telefono="+5491112345678", nombre="B"
    )

    assert a.id != b.id


async def _escenario_publico(db_session: AsyncSession) -> dict[str, object]:
    clinic = await crear_clinica(db_session)
    practica = await crear_practica(db_session, clinic)
    sillon = await crear_sillon(db_session, clinic)
    odonto = await crear_odontologo(db_session, clinic)
    await crear_horario(db_session, clinic, dia_semana=0, desde=time(8, 0), hasta=time(20, 0))
    return {
        "clinic": clinic,
        "practica": practica,
        "sillon": sillon,
        "odonto": odonto,
    }


@pytest.mark.asyncio
async def test_crear_turno_publico_calcula_sena_y_token(db_session: AsyncSession) -> None:
    base = await _escenario_publico(db_session)

    turno = await service.crear_turno_publico(
        db_session,
        nombre="Ana",
        telefono="+5491112345678",
        dni=None,
        practica_id=base["practica"].id,  # type: ignore[attr-defined]
        inicio=local(LUNES, time(10, 0)),
    )

    assert turno.estado == "pendiente_sena"
    assert turno.monto_sena == Decimal("2000.00")
    assert turno.reprogramaciones_count == 0
    assert turno.manage_token is not None
    assert len(turno.manage_token) >= 32
    assert turno.expira_at is not None
    delta = turno.expira_at - datetime.now(UTC)
    assert timedelta(minutes=25) < delta <= timedelta(minutes=30)


@pytest.mark.asyncio
async def test_crear_turno_publico_tokens_distintos(db_session: AsyncSession) -> None:
    base = await _escenario_publico(db_session)
    clinic = base["clinic"]
    await crear_sillon(db_session, clinic, "Sillón 2")
    await crear_odontologo(db_session, clinic)

    primero = await service.crear_turno_publico(
        db_session,
        nombre="Ana",
        telefono="+5491111111111",
        dni=None,
        practica_id=base["practica"].id,  # type: ignore[attr-defined]
        inicio=local(LUNES, time(10, 0)),
    )
    segundo = await service.crear_turno_publico(
        db_session,
        nombre="Beto",
        telefono="+5491122222222",
        dni=None,
        practica_id=base["practica"].id,  # type: ignore[attr-defined]
        inicio=local(LUNES, time(10, 0)),
    )

    assert primero.manage_token != segundo.manage_token
    assert primero.sillon_id != segundo.sillon_id or primero.odontologo_id != segundo.odontologo_id


@pytest.mark.asyncio
async def test_practica_inactiva_devuelve_404(db_session: AsyncSession) -> None:
    clinic = await crear_clinica(db_session)
    practica = await crear_practica(db_session, clinic, activa=False)

    with pytest.raises(NotFoundError):
        await service.crear_turno_publico(
            db_session,
            nombre="Ana",
            telefono="+5491112345678",
            dni=None,
            practica_id=practica.id,
            inicio=local(LUNES, time(10, 0)),
        )


@pytest.mark.asyncio
async def test_inicio_no_alineado_devuelve_409(db_session: AsyncSession) -> None:
    base = await _escenario_publico(db_session)

    with pytest.raises(ConflictError):
        await service.crear_turno_publico(
            db_session,
            nombre="Ana",
            telefono="+5491112345678",
            dni=None,
            practica_id=base["practica"].id,  # type: ignore[attr-defined]
            inicio=local(LUNES, time(10, 7)),
        )


@pytest.mark.asyncio
async def test_paciente_bloqueado_devuelve_403_con_fecha(db_session: AsyncSession) -> None:
    base = await _escenario_publico(db_session)
    clinic = base["clinic"]
    hasta = datetime.now(UTC) + timedelta(days=20)
    await crear_paciente(db_session, clinic, telefono="+5491112345678", bloqueado_hasta=hasta)

    with pytest.raises(ForbiddenError) as exc:
        await service.crear_turno_publico(
            db_session,
            nombre="Ana",
            telefono="+5491112345678",
            dni=None,
            practica_id=base["practica"].id,  # type: ignore[attr-defined]
            inicio=local(LUNES, time(10, 0)),
        )

    assert "bloqueado" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_paciente_con_bloqueo_vencido_puede_reservar(db_session: AsyncSession) -> None:
    base = await _escenario_publico(db_session)
    clinic = base["clinic"]
    await crear_paciente(
        db_session,
        clinic,
        telefono="+5491112345678",
        bloqueado_hasta=datetime.now(UTC) - timedelta(days=1),
    )

    turno = await service.crear_turno_publico(
        db_session,
        nombre="Ana",
        telefono="+5491112345678",
        dni=None,
        practica_id=base["practica"].id,  # type: ignore[attr-defined]
        inicio=local(LUNES, time(10, 0)),
    )

    assert turno.id is not None


@pytest.mark.asyncio
async def test_slot_ocupado_devuelve_409(db_session: AsyncSession) -> None:
    base = await _escenario_publico(db_session)
    clinic = base["clinic"]
    paciente = await crear_paciente(db_session, clinic)
    await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente,
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=local(LUNES, time(10, 0)),
    )

    with pytest.raises(ConflictError):
        await service.crear_turno_publico(
            db_session,
            nombre="Ana",
            telefono="+5491112345678",
            dni=None,
            practica_id=base["practica"].id,  # type: ignore[attr-defined]
            inicio=local(LUNES, time(10, 0)),
        )


@pytest.mark.asyncio
async def test_turno_cancelado_no_bloquea_el_slot(db_session: AsyncSession) -> None:
    base = await _escenario_publico(db_session)
    clinic = base["clinic"]
    paciente = await crear_paciente(db_session, clinic)
    await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente,
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=local(LUNES, time(10, 0)),
        estado="cancelado",
    )

    turno = await service.crear_turno_publico(
        db_session,
        nombre="Ana",
        telefono="+5491112345678",
        dni=None,
        practica_id=base["practica"].id,  # type: ignore[attr-defined]
        inicio=local(LUNES, time(10, 0)),
    )

    assert turno.id is not None


@pytest.mark.asyncio
async def test_expirar_pendientes_solo_vencidos(db_session: AsyncSession) -> None:
    base = await _escenario_publico(db_session)
    clinic = base["clinic"]
    paciente = await crear_paciente(db_session, clinic)
    ahora = datetime.now(UTC)
    vencido = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente,
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=local(LUNES, time(10, 0)),
        estado="pendiente_sena",
        expira_at=ahora - timedelta(minutes=1),
    )
    confirmado = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente,
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=local(LUNES, time(11, 0)),
        estado="confirmado",
    )

    cantidad = await service.expirar_pendientes(db_session, now=ahora)
    assert cantidad == 1
    assert vencido.estado == "cancelado"
    assert confirmado.estado == "confirmado"

    # Idempotente: la segunda corrida no cambia nada.
    assert await service.expirar_pendientes(db_session, now=ahora) == 0


@pytest.mark.asyncio
async def test_barrido_perezoso_libera_slot(db_session: AsyncSession) -> None:
    base = await _escenario_publico(db_session)
    clinic = base["clinic"]
    paciente = await crear_paciente(db_session, clinic)
    await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente,
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=local(LUNES, time(10, 0)),
        estado="pendiente_sena",
        expira_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    dia = await service.obtener_slots(
        db_session,
        practica_id=base["practica"].id,
        fecha=LUNES,  # type: ignore[attr-defined]
    )

    horas = [
        slot.inicio.astimezone(local(LUNES, time(0, 0)).tzinfo).strftime("%H:%M")
        for slot in dia.slots
    ]
    assert "10:00" in horas


@pytest.mark.asyncio
async def test_foto_monto_sena_no_cambia_con_el_porcentaje(db_session: AsyncSession) -> None:
    base = await _escenario_publico(db_session)
    practica = base["practica"]

    turno = await service.crear_turno_publico(
        db_session,
        nombre="Ana",
        telefono="+5491112345678",
        dni=None,
        practica_id=practica.id,  # type: ignore[attr-defined]
        inicio=local(LUNES, time(10, 0)),
    )
    assert turno.monto_sena == Decimal("2000.00")

    practica.sena_pct = 80  # type: ignore[attr-defined]
    await db_session.flush()
    await db_session.refresh(turno)

    assert turno.monto_sena == Decimal("2000.00")


@pytest.mark.asyncio
async def test_inicio_con_offset_se_respeta(db_session: AsyncSession) -> None:
    base = await _escenario_publico(db_session)

    turno = await service.crear_turno_publico(
        db_session,
        nombre="Ana",
        telefono="+5491112345678",
        dni=None,
        practica_id=base["practica"].id,  # type: ignore[attr-defined]
        inicio=local(LUNES, time(10, 0)).astimezone(UTC),
    )

    assert turno.inicio == local(LUNES, time(10, 0)).astimezone(UTC)


@pytest.mark.asyncio
async def test_turno_guardado_pertenece_a_la_clinica_de_la_practica(
    db_session: AsyncSession,
) -> None:
    base = await _escenario_publico(db_session)

    turno = await service.crear_turno_publico(
        db_session,
        nombre="Ana",
        telefono="+5491112345678",
        dni=None,
        practica_id=base["practica"].id,  # type: ignore[attr-defined]
        inicio=local(LUNES, time(10, 0)),
    )

    result = await db_session.execute(select(Turno).where(Turno.id == turno.id))
    guardado = result.scalar_one()
    assert guardado.clinic_id == base["clinic"].id  # type: ignore[attr-defined]
    assert guardado.paciente_id is not None
