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
from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnprocessableError
from app.core.logging import get_logger
from app.domain.clinica.catalogo_service import precio_efectivo
from app.domain.clinica.models import Clinic, Sillon, TipoPractica
from app.domain.clinica.repository import (
    ArancelRepository,
    ClinicRepository,
    SillonRepository,
    TipoPracticaRepository,
)
from app.domain.notificaciones import NoOpRecordatorio, RecordatorioPort
from app.domain.personas.models import Paciente, User
from app.domain.personas.repository import PacienteRepository, UserRepository
from app.domain.turnos.gestion import (
    CODIGO_ESTADO_NO_GESTIONABLE,
    CODIGO_REQUIERE_CONFIRMACION,
    CODIGO_REQUIERE_NUEVA_SENA,
    CODIGO_SLOT_INVALIDO,
    CODIGO_SOLAPE,
    CODIGO_TOKEN_INVALIDO,
    CODIGO_TURNO_NO_ENCONTRADO,
    dentro_de_ventana,
    es_gestionable,
)
from app.domain.turnos.models import Turno
from app.domain.turnos.repository import HorarioAtencionRepository, TurnoRepository
from app.domain.turnos.slots import Slot, esta_alineado, generar_slots, slot_para_inicio

logger = get_logger(__name__)


@dataclass
class SlotsDia:
    """Resultado de `GET /api/public/slots`."""

    practica: TipoPractica
    fecha: date
    duracion_min: int
    slots: list[Slot]


@dataclass
class GestionPublica:
    """Vista de gestión resuelta a partir de un `manage_token`."""

    turno: Turno
    clinic: Clinic
    practica: TipoPractica
    dentro_de_ventana: bool
    reprogramaciones_restantes: int


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
    excluir_turno_id: UUID | None = None,
) -> list[Slot]:
    horarios = await HorarioAtencionRepository(session).list_by_dia(clinic.id, fecha.weekday())
    if not horarios:
        return []

    inicio, fin = _rango_dia_utc(fecha, zona)
    turnos = await TurnoRepository(session).list_vigentes_en_rango(clinic.id, inicio, fin)
    if excluir_turno_id is not None:
        turnos = [turno for turno in turnos if turno.id != excluir_turno_id]
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


async def resolver_gestion_publica(
    session: AsyncSession,
    *,
    token: str,
    now: datetime | None = None,
) -> GestionPublica:
    """Resolver un turno por su `manage_token` para el canal público.

    Un token inválido responde 403 (nunca 401, design D4). Un turno borrado
    lógicamente responde 404. La comparación usa `secrets.compare_digest` para
    no filtrar información por tiempo.
    """
    if not token:
        raise ForbiddenError("El enlace de gestión no es válido", code=CODIGO_TOKEN_INVALIDO)

    turno = await TurnoRepository(session).get_by_manage_token(token)
    if (
        turno is None
        or turno.manage_token is None
        or not secrets.compare_digest(turno.manage_token, token)
    ):
        raise ForbiddenError("El enlace de gestión no es válido", code=CODIGO_TOKEN_INVALIDO)

    if not turno.is_active:
        raise NotFoundError("Turno no encontrado", code=CODIGO_TURNO_NO_ENCONTRADO)

    clinic = await ClinicRepository(session).get(turno.clinic_id)
    if clinic is None or not clinic.is_active:
        raise NotFoundError("Turno no encontrado", code=CODIGO_TURNO_NO_ENCONTRADO)

    practica = await TipoPracticaRepository(session).get(turno.tipo_practica_id)
    if practica is None:
        raise NotFoundError("Turno no encontrado", code=CODIGO_TURNO_NO_ENCONTRADO)

    ahora = _aware_utc(now) if now is not None else datetime.now(UTC)
    return GestionPublica(
        turno=turno,
        clinic=clinic,
        practica=practica,
        dentro_de_ventana=dentro_de_ventana(_aware_utc(turno.inicio), ahora, _zona(clinic)),
        reprogramaciones_restantes=max(0, 1 - turno.reprogramaciones_count),
    )


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
        raise ConflictError("El horario seleccionado ya no está disponible", code=CODIGO_SOLAPE)

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
        raise ConflictError(
            "El horario seleccionado ya no está disponible", code=CODIGO_SOLAPE
        ) from exc
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


def _tiene_sena_aprobada(turno: Turno) -> bool:
    """Proxy de seña aprobada hasta que C-08 introduzca `Pago`.

    Un turno `pendiente_sena` todavía no pagó; uno `confirmado` con monto
    positivo sí. C-08 reemplaza este proxy por la consulta real al pago.
    """
    return turno.estado == "confirmado" and turno.monto_sena > 0


async def cancelar_turno(
    session: AsyncSession,
    *,
    turno: Turno,
    clinic: Clinic,
    confirmar_perdida_sena: bool = False,
    motivo: str | None = None,
    usuario_id: UUID | None = None,
    now: datetime | None = None,
    recordatorio: RecordatorioPort | None = None,
) -> Turno:
    """Cancelar un turno vigente liberando el horario de inmediato.

    Dentro de la ventana de 12 horas no toca la seña. Fuera de la ventana y con
    una seña aprobada exige `confirmar_perdida_sena`; si se confirma, marca la
    seña como perdida. Un turno sin seña aprobada nunca la marca.
    """
    ahora = _aware_utc(now) if now is not None else datetime.now(UTC)
    if not es_gestionable(turno.estado):
        raise ConflictError(
            f"El turno está en estado {turno.estado} y no se puede gestionar",
            code=CODIGO_ESTADO_NO_GESTIONABLE,
        )

    zona = _zona(clinic)
    tardia = not dentro_de_ventana(_aware_utc(turno.inicio), ahora, zona)
    perdida = tardia and _tiene_sena_aprobada(turno)
    if perdida and not confirmar_perdida_sena:
        raise ConflictError(
            "Cancelar dentro de las 12 horas hace perder la seña",
            code=CODIGO_REQUIERE_CONFIRMACION,
            extra={"perdida_sena": True},
        )

    turno.estado = "cancelado"
    turno.sena_perdida = perdida
    await session.commit()

    logger.info(
        "turno_cancelado",
        turno_id=str(turno.id),
        clinic_id=str(turno.clinic_id),
        usuario_id=str(usuario_id) if usuario_id else None,
        motivo=motivo,
        perdida_sena=perdida,
    )
    await (recordatorio or NoOpRecordatorio()).cancelar(turno.id)
    return turno


async def _resolver_slot_nuevo(
    session: AsyncSession,
    *,
    turno: Turno,
    practica: TipoPractica,
    clinic: Clinic,
    inicio_utc: datetime,
    zona: ZoneInfo,
    fecha_local: date,
) -> Slot:
    """Validar que el horario pedido exista, esté alineado y siga libre."""
    horarios = await HorarioAtencionRepository(session).list_by_dia(
        clinic.id, fecha_local.weekday()
    )
    if not esta_alineado(
        inicio=inicio_utc,
        fecha=fecha_local,
        duracion_min=practica.duracion_min,
        horarios=horarios,
        tz=clinic.timezone or settings.tz_clinica,
    ):
        raise UnprocessableError(
            "El horario pedido no está alineado con la agenda",
            code=CODIGO_SLOT_INVALIDO,
        )

    slots = await _slots_del_dia(
        session,
        practica=practica,
        clinic=clinic,
        fecha=fecha_local,
        zona=zona,
        excluir_turno_id=turno.id,
    )
    slot = slot_para_inicio(slots, inicio_utc)
    if slot is None:
        raise ConflictError(
            "El horario seleccionado ya no está disponible",
            code=CODIGO_SOLAPE,
        )
    return slot


async def reprogramar_turno(
    session: AsyncSession,
    *,
    turno: Turno,
    clinic: Clinic,
    nuevo_inicio: datetime,
    confirmar_perdida_sena: bool = False,
    motivo: str | None = None,
    usuario_id: UUID | None = None,
    now: datetime | None = None,
    recordatorio: RecordatorioPort | None = None,
) -> Turno:
    """Mover un turno vigente a otro slot libre.

    La primera reprogramación muta el turno en el lugar (la seña viaja). Desde
    la segunda, y solo con `confirmar_perdida_sena`, cierra el turno anterior
    como `cancelado` con la seña perdida y crea uno nuevo en `pendiente_sena`
    enlazado por `reprogramado_de_id`.
    """
    ahora = _aware_utc(now) if now is not None else datetime.now(UTC)
    if not es_gestionable(turno.estado):
        raise ConflictError(
            f"El turno está en estado {turno.estado} y no se puede gestionar",
            code=CODIGO_ESTADO_NO_GESTIONABLE,
        )

    practica = await TipoPracticaRepository(session).get_by_clinic(
        clinic.id, turno.tipo_practica_id
    )
    if practica is None:
        raise NotFoundError("Práctica no encontrada o inactiva")

    zona = _zona(clinic)
    inicio_utc = _normalizar_inicio(nuevo_inicio, zona)
    fecha_local = inicio_utc.astimezone(zona).date()
    slot = await _resolver_slot_nuevo(
        session,
        turno=turno,
        practica=practica,
        clinic=clinic,
        inicio_utc=inicio_utc,
        zona=zona,
        fecha_local=fecha_local,
    )

    tardia = not dentro_de_ventana(_aware_utc(turno.inicio), ahora, zona) or not dentro_de_ventana(
        inicio_utc, ahora, zona
    )
    port = recordatorio or NoOpRecordatorio()

    if turno.reprogramaciones_count >= 1:
        if not confirmar_perdida_sena:
            raise ConflictError(
                "La segunda reprogramación exige una seña nueva",
                code=CODIGO_REQUIERE_NUEVA_SENA,
            )
        return await _segunda_reprogramacion(
            session,
            turno=turno,
            practica=practica,
            clinic=clinic,
            slot=slot,
            fecha_local=fecha_local,
            ahora=ahora,
            motivo=motivo,
            usuario_id=usuario_id,
            port=port,
        )

    if tardia and not confirmar_perdida_sena and _tiene_sena_aprobada(turno):
        raise ConflictError(
            "Reprogramar dentro de las 12 horas hace perder la seña",
            code=CODIGO_REQUIERE_CONFIRMACION,
            extra={"perdida_sena": True},
        )

    turno.sillon_id = slot.sillon_id
    turno.odontologo_id = slot.odontologo_id
    turno.inicio = slot.inicio
    turno.fin = slot.fin
    turno.reprogramaciones_count = 1
    if tardia:
        turno.sena_perdida = True
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "El horario seleccionado ya no está disponible", code=CODIGO_SOLAPE
        ) from exc
    await session.commit()

    logger.info(
        "turno_reprogramado",
        turno_id=str(turno.id),
        clinic_id=str(turno.clinic_id),
        usuario_id=str(usuario_id) if usuario_id else None,
        motivo=motivo,
        nuevo_inicio=turno.inicio.isoformat(),
        segunda=False,
    )
    await port.reprogramar(turno.id, turno.inicio)
    return turno


async def _segunda_reprogramacion(
    session: AsyncSession,
    *,
    turno: Turno,
    practica: TipoPractica,
    clinic: Clinic,
    slot: Slot,
    fecha_local: date,
    ahora: datetime,
    motivo: str | None,
    usuario_id: UUID | None,
    port: RecordatorioPort,
) -> Turno:
    """Cerrar el turno anterior con la seña perdida y crear el nuevo."""
    monto_sena = await calcular_monto_sena(session, practica=practica, fecha=fecha_local)
    nuevo = Turno(
        clinic_id=turno.clinic_id,
        paciente_id=turno.paciente_id,
        sillon_id=slot.sillon_id,
        odontologo_id=slot.odontologo_id,
        tipo_practica_id=turno.tipo_practica_id,
        inicio=slot.inicio,
        fin=slot.fin,
        estado="pendiente_sena",
        manage_token=secrets.token_urlsafe(32),
        reprogramaciones_count=1,
        monto_sena=monto_sena,
        sena_perdida=False,
        expira_at=ahora + timedelta(minutes=settings.mp_ttl_min),
        reprogramado_de_id=turno.id,
        is_active=True,
    )
    turno.estado = "cancelado"
    turno.sena_perdida = True
    session.add(nuevo)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise ConflictError(
            "El horario seleccionado ya no está disponible", code=CODIGO_SOLAPE
        ) from exc
    await session.commit()

    logger.info(
        "turno_reprogramado",
        turno_id=str(nuevo.id),
        turno_anterior_id=str(turno.id),
        clinic_id=str(nuevo.clinic_id),
        usuario_id=str(usuario_id) if usuario_id else None,
        motivo=motivo,
        nuevo_inicio=nuevo.inicio.isoformat(),
        segunda=True,
    )
    await port.cancelar(turno.id)
    await port.reprogramar(nuevo.id, nuevo.inicio)
    return nuevo


async def _cargar_turno_de_clinica(
    session: AsyncSession, *, clinic_id: UUID, turno_id: UUID
) -> tuple[Turno, Clinic]:
    """Resolver un turno del canal interno sin revelar los de otra clínica.

    Aislamiento de clínica responde 404 (nunca 403) para no filtrar existencia.
    """
    turno = await TurnoRepository(session).get(turno_id)
    if turno is None or turno.clinic_id != clinic_id or not turno.is_active:
        raise NotFoundError("Turno no encontrado", code=CODIGO_TURNO_NO_ENCONTRADO)
    clinic = await ClinicRepository(session).get(clinic_id)
    if clinic is None or not clinic.is_active:
        raise NotFoundError("Turno no encontrado", code=CODIGO_TURNO_NO_ENCONTRADO)
    return turno, clinic


async def cancelar_turno_interno(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    turno_id: UUID,
    motivo: str,
    usuario_id: UUID | None = None,
    confirmar_perdida_sena: bool = False,
    now: datetime | None = None,
    recordatorio: RecordatorioPort | None = None,
) -> Turno:
    """Cancelar desde el panel reutilizando las reglas del canal público."""
    turno, clinic = await _cargar_turno_de_clinica(session, clinic_id=clinic_id, turno_id=turno_id)
    return await cancelar_turno(
        session,
        turno=turno,
        clinic=clinic,
        confirmar_perdida_sena=confirmar_perdida_sena,
        motivo=motivo,
        usuario_id=usuario_id,
        now=now,
        recordatorio=recordatorio,
    )


async def reprogramar_turno_interno(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    turno_id: UUID,
    nuevo_inicio: datetime,
    motivo: str,
    usuario_id: UUID | None = None,
    confirmar_perdida_sena: bool = False,
    now: datetime | None = None,
    recordatorio: RecordatorioPort | None = None,
) -> Turno:
    """Reprogramar desde el panel reutilizando las reglas del canal público."""
    turno, clinic = await _cargar_turno_de_clinica(session, clinic_id=clinic_id, turno_id=turno_id)
    return await reprogramar_turno(
        session,
        turno=turno,
        clinic=clinic,
        nuevo_inicio=nuevo_inicio,
        confirmar_perdida_sena=confirmar_perdida_sena,
        motivo=motivo,
        usuario_id=usuario_id,
        now=now,
        recordatorio=recordatorio,
    )


__all__ = [
    "GestionPublica",
    "SlotsDia",
    "calcular_monto_sena",
    "cancelar_turno",
    "cancelar_turno_interno",
    "crear_turno_interno",
    "crear_turno_publico",
    "expirar_pendientes",
    "obtener_slots",
    "reprogramar_turno",
    "reprogramar_turno_interno",
    "resolver_gestion_publica",
]
