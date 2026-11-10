"""Servicio del motor de turnos: slots, reservas y expiración (C-05)."""

import secrets
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, cast
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.domain.clinica.catalogo_service import precio_efectivo
from app.domain.clinica.models import Clinic, Sillon, TipoPractica
from app.domain.clinica.repository import (
    ArancelRepository,
    ClinicRepository,
    SillonRepository,
    TipoPracticaRepository,
)
from app.domain.personas.models import Paciente, User
from app.domain.personas.repository import PacienteRepository, UserRepository
from app.domain.turnos.models import Turno
from app.domain.turnos.repository import HorarioAtencionRepository, TurnoRepository
from app.domain.turnos.slots import Slot, generar_slots, slot_para_inicio


@dataclass
class SlotsDia:
    """Resultado de `GET /api/public/slots`."""

    practica: TipoPractica
    fecha: date
    duracion_min: int
    slots: list[Slot]


def _aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _zona(clinic: Clinic) -> ZoneInfo:
    return ZoneInfo(clinic.timezone or settings.tz_clinica)


def _normalizar_inicio(inicio: datetime, zona: ZoneInfo) -> datetime:
    if inicio.tzinfo is None:
        return inicio.replace(tzinfo=zona).astimezone(UTC)
    return inicio.astimezone(UTC)


def _rango_dia_utc(fecha: date, zona: ZoneInfo) -> tuple[datetime, datetime]:
    inicio = datetime.combine(fecha, time.min, tzinfo=zona).astimezone(UTC)
    fin = datetime.combine(fecha + timedelta(days=1), time.min, tzinfo=zona).astimezone(UTC)
    return inicio, fin


async def _cargar_practica(session: AsyncSession, practica_id: UUID) -> tuple[TipoPractica, Clinic]:
    practica = await TipoPracticaRepository(session).get(practica_id)
    if practica is None or not practica.activa or not practica.is_active:
        raise NotFoundError("Práctica no encontrada o inactiva")
    clinic = await ClinicRepository(session).get(practica.clinic_id)
    if clinic is None or not clinic.is_active:
        raise NotFoundError("Clínica no encontrada o inactiva")
    return practica, clinic


async def _slots_del_dia(
    session: AsyncSession,
    *,
    practica: TipoPractica,
    clinic: Clinic,
    fecha: date,
    zona: ZoneInfo,
) -> list[Slot]:
    horarios = await HorarioAtencionRepository(session).list_by_dia(clinic.id, fecha.weekday())
    if not horarios:
        return []

    inicio, fin = _rango_dia_utc(fecha, zona)
    turnos = await TurnoRepository(session).list_vigentes_en_rango(clinic.id, inicio, fin)
    sillones = await SillonRepository(session).list_activos(clinic.id)
    odontologos = await UserRepository(session).list_odontologos(clinic.id)

    return generar_slots(
        fecha=fecha,
        duracion_min=practica.duracion_min,
        horarios=horarios,
        turnos_vigentes=turnos,
        sillones=sillones,
        odontologos=odontologos,
        tz=clinic.timezone or settings.tz_clinica,
    )


def _verificar_bloqueo(paciente: Paciente, ahora: datetime) -> None:
    bloqueado_hasta = paciente.bloqueado_hasta
    if bloqueado_hasta is not None and _aware_utc(bloqueado_hasta) > ahora:
        raise ForbiddenError(f"Paciente bloqueado hasta {_aware_utc(bloqueado_hasta).isoformat()}")


async def calcular_monto_sena(
    session: AsyncSession, *, practica: TipoPractica, fecha: date
) -> Decimal:
    """Foto de la seña al reservar: precio efectivo × % de la práctica."""
    arancel = await ArancelRepository(session).get_by_tipo(practica.id)
    precio = precio_efectivo(practica, arancel, fecha)
    monto = precio * Decimal(practica.sena_pct) / Decimal(100)
    return monto.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def expirar_pendientes(session: AsyncSession, *, now: datetime | None = None) -> int:
    """Pasar a `cancelado` los turnos `pendiente_sena` vencidos (DB-first)."""
    ahora = _aware_utc(now) if now is not None else datetime.now(UTC)
    resultado = cast(
        CursorResult[Any],
        await session.execute(
            update(Turno)
            .where(
                Turno.estado == "pendiente_sena",
                Turno.expira_at.is_not(None),
                Turno.expira_at <= ahora,
            )
            .values(estado="cancelado")
        ),
    )
    return int(resultado.rowcount or 0)


async def obtener_slots(
    session: AsyncSession,
    *,
    practica_id: UUID,
    fecha: date,
    now: datetime | None = None,
) -> SlotsDia:
    """Slots disponibles de un día, liberando antes los vencidos."""
    expirados = await expirar_pendientes(session, now=now)
    if expirados:
        await session.commit()
    practica, clinic = await _cargar_practica(session, practica_id)
    zona = _zona(clinic)
    slots = await _slots_del_dia(session, practica=practica, clinic=clinic, fecha=fecha, zona=zona)
    return SlotsDia(practica=practica, fecha=fecha, duracion_min=practica.duracion_min, slots=slots)


async def crear_turno_publico(
    session: AsyncSession,
    *,
    nombre: str,
    telefono: str,
    dni: str | None,
    practica_id: UUID,
    inicio: datetime,
    now: datetime | None = None,
) -> Turno:
    """Crear una reserva pública sin login y emitir su `manage_token`."""
    ahora = _aware_utc(now) if now is not None else datetime.now(UTC)
    await expirar_pendientes(session, now=ahora)

    practica, clinic = await _cargar_practica(session, practica_id)
    zona = _zona(clinic)
    inicio_utc = _normalizar_inicio(inicio, zona)
    fecha_local = inicio_utc.astimezone(zona).date()

    slots = await _slots_del_dia(
        session, practica=practica, clinic=clinic, fecha=fecha_local, zona=zona
    )
    slot = slot_para_inicio(slots, inicio_utc)
    if slot is None:
        raise ConflictError("El horario seleccionado ya no está disponible")

    paciente = await PacienteRepository(session).get_or_create_by_telefono(
        clinic_id=clinic.id, telefono=telefono, nombre=nombre, dni=dni
    )
    _verificar_bloqueo(paciente, ahora)

    monto_sena = await calcular_monto_sena(session, practica=practica, fecha=fecha_local)
    turno = Turno(
        clinic_id=clinic.id,
        paciente_id=paciente.id,
        sillon_id=slot.sillon_id,
        odontologo_id=slot.odontologo_id,
        tipo_practica_id=practica.id,
        inicio=slot.inicio,
        fin=slot.fin,
        estado="pendiente_sena",
        manage_token=secrets.token_urlsafe(32),
        reprogramaciones_count=0,
        monto_sena=monto_sena,
        expira_at=ahora + timedelta(minutes=settings.mp_ttl_min),
        is_active=True,
    )
    session.add(turno)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("El horario seleccionado ya no está disponible") from exc
    await session.commit()
    return turno


async def crear_turno_interno(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    paciente_id: UUID,
    sillon_id: UUID,
    odontologo_id: UUID,
    tipo_practica_id: UUID,
    inicio: datetime,
    now: datetime | None = None,
) -> Turno:
    """Crear una reserva interna (recepción/admin) sin token público."""
    ahora = _aware_utc(now) if now is not None else datetime.now(UTC)
    await expirar_pendientes(session, now=ahora)

    practica = await TipoPracticaRepository(session).get_by_clinic(clinic_id, tipo_practica_id)
    if practica is None or not practica.activa or not practica.is_active:
        raise NotFoundError("Práctica no encontrada o inactiva")

    pacientes = PacienteRepository(session)
    paciente = await pacientes.get(paciente_id)
    if paciente is None or paciente.clinic_id != clinic_id:
        raise NotFoundError("Paciente no encontrado")

    sillon: Sillon | None = await SillonRepository(session).get(sillon_id)
    if sillon is None or sillon.clinic_id != clinic_id or not sillon.activo:
        raise NotFoundError("Sillón no encontrado")

    odontologo: User | None = await UserRepository(session).get(odontologo_id)
    if (
        odontologo is None
        or odontologo.clinic_id != clinic_id
        or odontologo.rol != "odonto"
        or not odontologo.activo
        or not odontologo.is_active
    ):
        raise NotFoundError("Odontólogo no encontrado")

    clinic = await ClinicRepository(session).get(clinic_id)
    if clinic is None:
        raise NotFoundError("Clínica no encontrada")
    zona = _zona(clinic)
    inicio_utc = _normalizar_inicio(inicio, zona)
    fin_utc = inicio_utc + timedelta(minutes=practica.duracion_min)

    turnos = TurnoRepository(session)
    if await turnos.get_solape_sillon(sillon.id, inicio_utc, fin_utc) is not None:
        raise ConflictError("El sillón ya está ocupado en ese horario")
    if await turnos.get_solape_odontologo(odontologo.id, inicio_utc, fin_utc) is not None:
        raise ConflictError("El odontólogo ya está ocupado en ese horario")

    _verificar_bloqueo(paciente, ahora)
    monto_sena = await calcular_monto_sena(
        session, practica=practica, fecha=inicio_utc.astimezone(zona).date()
    )

    turno = Turno(
        clinic_id=clinic_id,
        paciente_id=paciente.id,
        sillon_id=sillon.id,
        odontologo_id=odontologo.id,
        tipo_practica_id=practica.id,
        inicio=inicio_utc,
        fin=fin_utc,
        estado="confirmado",
        manage_token=None,
        reprogramaciones_count=0,
        monto_sena=monto_sena,
        expira_at=None,
        is_active=True,
    )
    session.add(turno)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError("El horario seleccionado ya no está disponible") from exc
    await session.commit()
    return turno


__all__ = [
    "SlotsDia",
    "calcular_monto_sena",
    "crear_turno_interno",
    "crear_turno_publico",
    "expirar_pendientes",
    "obtener_slots",
]
