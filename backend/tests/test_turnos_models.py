"""Tests de modelos del motor de turnos: Turno y HorarioAtencion (C-05)."""

from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clinica.models import Clinic, Sillon, TipoPractica
from app.domain.personas.models import Paciente, User
from app.domain.turnos.models import HorarioAtencion, Turno

AHORA = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)


async def _base(db_session: AsyncSession) -> dict[str, object]:
    clinic = Clinic(nombre=f"Clínica {uuid4()}", is_active=True)
    db_session.add(clinic)
    await db_session.flush()

    paciente = Paciente(
        clinic_id=clinic.id,
        nombre="Ana Paciente",
        telefono=f"+54911{uuid4().hex[:8]}",
        dni=None,
        is_active=True,
    )
    sillon = Sillon(clinic_id=clinic.id, nombre="Sillón 1", activo=True, is_active=True)
    odonto = User(
        clinic_id=clinic.id,
        email=f"odonto-{uuid4().hex[:8]}@clinica.com",
        password_hash="x",
        rol="odonto",
        activo=True,
        is_active=True,
    )
    practica = TipoPractica(
        clinic_id=clinic.id,
        nombre="Limpieza",
        duracion_min=30,
        precio_base=Decimal("10000.00"),
        sena_pct=20,
        activa=True,
        is_active=True,
    )
    db_session.add_all([paciente, sillon, odonto, practica])
    await db_session.flush()
    return {
        "clinic": clinic,
        "paciente": paciente,
        "sillon": sillon,
        "odonto": odonto,
        "practica": practica,
    }


def _turno(base: dict[str, object], **overrides: object) -> Turno:
    values: dict[str, object] = {
        "clinic_id": base["clinic"].id,  # type: ignore[attr-defined]
        "paciente_id": base["paciente"].id,  # type: ignore[attr-defined]
        "sillon_id": base["sillon"].id,  # type: ignore[attr-defined]
        "odontologo_id": base["odonto"].id,  # type: ignore[attr-defined]
        "tipo_practica_id": base["practica"].id,  # type: ignore[attr-defined]
        "inicio": AHORA,
        "fin": AHORA + timedelta(minutes=30),
        "estado": "pendiente_sena",
        "monto_sena": Decimal("2000.00"),
        "is_active": True,
    }
    values.update(overrides)
    return Turno(**values)


@pytest.mark.asyncio
async def test_crear_turno_pendiente_sena(db_session: AsyncSession) -> None:
    base = await _base(db_session)
    turno = _turno(base, manage_token="token-unico")
    db_session.add(turno)
    await db_session.flush()

    assert turno.id is not None
    assert turno.estado == "pendiente_sena"
    assert turno.reprogramaciones_count == 0
    assert turno.monto_sena == Decimal("2000.00")
    assert turno.manage_token == "token-unico"
    assert turno.expira_at is None


@pytest.mark.asyncio
async def test_check_fin_mayor_que_inicio(db_session: AsyncSession) -> None:
    base = await _base(db_session)
    db_session.add(_turno(base, inicio=AHORA, fin=AHORA - timedelta(minutes=30)))

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_check_monto_sena_no_negativo(db_session: AsyncSession) -> None:
    base = await _base(db_session)
    db_session.add(_turno(base, monto_sena=Decimal("-1.00")))

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_check_estado_valido(db_session: AsyncSession) -> None:
    base = await _base(db_session)
    db_session.add(_turno(base, estado="volando"))

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_manage_token_unico(db_session: AsyncSession) -> None:
    base = await _base(db_session)
    db_session.add(_turno(base, manage_token="repetido"))
    await db_session.flush()
    db_session.add(
        _turno(
            base,
            inicio=AHORA + timedelta(hours=1),
            fin=AHORA + timedelta(hours=1, minutes=30),
            manage_token="repetido",
            sillon_id=None,
            odontologo_id=None,
        )
    )

    # En SQLite no hay EXCLUDE; el UNIQUE de manage_token sí está.
    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_horario_atencion_unique_por_dia_y_hora(db_session: AsyncSession) -> None:
    base = await _base(db_session)
    clinic = base["clinic"]
    db_session.add(
        HorarioAtencion(
            clinic_id=clinic.id,  # type: ignore[attr-defined]
            dia_semana=0,
            hora_desde=time(8, 0),
            hora_hasta=time(20, 0),
            activo=True,
            is_active=True,
        )
    )
    await db_session.flush()
    db_session.add(
        HorarioAtencion(
            clinic_id=clinic.id,  # type: ignore[attr-defined]
            dia_semana=0,
            hora_desde=time(8, 0),
            hora_hasta=time(12, 0),
            activo=True,
            is_active=True,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_horario_check_hora_hasta_mayor(db_session: AsyncSession) -> None:
    base = await _base(db_session)
    clinic = base["clinic"]
    db_session.add(
        HorarioAtencion(
            clinic_id=clinic.id,  # type: ignore[attr-defined]
            dia_semana=1,
            hora_desde=time(20, 0),
            hora_hasta=time(8, 0),
            activo=True,
            is_active=True,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_paciente_telefono_unico_por_clinica(db_session: AsyncSession) -> None:
    base = await _base(db_session)
    clinic = base["clinic"]
    db_session.add(
        Paciente(
            clinic_id=clinic.id,  # type: ignore[attr-defined]
            nombre="Otra",
            telefono=base["paciente"].telefono,  # type: ignore[attr-defined]
            dni=None,
            is_active=True,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()


@pytest.mark.asyncio
async def test_paciente_dni_y_bloqueado_hasta_son_nullable(db_session: AsyncSession) -> None:
    base = await _base(db_session)
    paciente = base["paciente"]
    assert paciente.dni is None  # type: ignore[attr-defined]
    assert paciente.bloqueado_hasta is None  # type: ignore[attr-defined]
