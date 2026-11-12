"""Generación pura de slots disponibles (C-05).

La función no toca la base: recibe franjas, turnos y recursos ya cargados y
devuelve huecos alineados a la duración de la práctica en UTC. Un slot puede
terminar justo en `hora_hasta` (el cierre es inclusivo para el fin del turno),
tal como define el design D4 del change.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Protocol
from uuid import UUID
from zoneinfo import ZoneInfo

from app.core.config import settings

ESTADOS_VIGENTES = ("pendiente_sena", "confirmado", "reprogramado")


class _HorarioLike(Protocol):
    dia_semana: int
    hora_desde: time
    hora_hasta: time
    activo: bool


class _TurnoLike(Protocol):
    inicio: datetime
    fin: datetime
    sillon_id: UUID
    odontologo_id: UUID
    estado: str


class _RecursoLike(Protocol):
    id: UUID
    activo: bool


@dataclass(frozen=True)
class Slot:
    """Hueco reservable con el sillón y odontólogo asignados."""

    inicio: datetime
    fin: datetime
    sillon_id: UUID
    odontologo_id: UUID


def _aware_utc(value: datetime) -> datetime:
    """Normalizar datetimes (SQLite devuelve naive) a UTC con offset."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _solapa(inicio: datetime, fin: datetime, otro_inicio: datetime, otro_fin: datetime) -> bool:
    return inicio < otro_fin and otro_inicio < fin


def generar_slots(
    *,
    fecha: date,
    duracion_min: int,
    horarios: Sequence[_HorarioLike],
    turnos_vigentes: Sequence[_TurnoLike],
    sillones: Sequence[_RecursoLike],
    odontologos: Sequence[_RecursoLike],
    tz: str | None = None,
) -> list[Slot]:
    """Generar los slots libres de un día para una práctica.

    Pasos: filtrar franjas del día, recorrer en pasos de `duracion_min` sin
    llegar a `hora_hasta`, descartar superposiciones y asignar el primer par
    (sillón activo, odontólogo activo) libre.
    """
    if duracion_min <= 0:
        raise ValueError("duracion_min debe ser mayor a cero")

    zona = ZoneInfo(tz or settings.tz_clinica)
    duracion = timedelta(minutes=duracion_min)

    sillones_libres = [recurso for recurso in sillones if getattr(recurso, "activo", True)]
    odontologos_libres = [recurso for recurso in odontologos if getattr(recurso, "activo", True)]
    if not sillones_libres or not odontologos_libres:
        return []

    ocupados: list[tuple[UUID, UUID, datetime, datetime]] = [
        (
            turno.sillon_id,
            turno.odontologo_id,
            _aware_utc(turno.inicio),
            _aware_utc(turno.fin),
        )
        for turno in turnos_vigentes
        if getattr(turno, "estado", "confirmado") in ESTADOS_VIGENTES
    ]

    slots: list[Slot] = []
    vistos: set[tuple[datetime, UUID, UUID]] = set()

    for horario in sorted(horarios, key=lambda item: item.hora_desde):
        if not getattr(horario, "activo", True):
            continue
        if horario.dia_semana != fecha.weekday():
            continue

        franja_inicio = datetime.combine(fecha, horario.hora_desde, tzinfo=zona).astimezone(UTC)
        franja_fin = datetime.combine(fecha, horario.hora_hasta, tzinfo=zona).astimezone(UTC)

        inicio = franja_inicio
        while inicio + duracion <= franja_fin:
            fin = inicio + duracion
            asignado = None
            for sillon in sillones_libres:
                if any(
                    ocupado_sillon == sillon.id
                    and _solapa(inicio, fin, ocupado_inicio, ocupado_fin)
                    for ocupado_sillon, _, ocupado_inicio, ocupado_fin in ocupados
                ):
                    continue
                for odontologo in odontologos_libres:
                    if any(
                        ocupado_odonto == odontologo.id
                        and _solapa(inicio, fin, ocupado_inicio, ocupado_fin)
                        for _, ocupado_odonto, ocupado_inicio, ocupado_fin in ocupados
                    ):
                        continue
                    asignado = (sillon, odontologo)
                    break
                if asignado is not None:
                    break

            if asignado is not None:
                clave = (inicio, asignado[0].id, asignado[1].id)
                if clave not in vistos:
                    vistos.add(clave)
                    slots.append(
                        Slot(
                            inicio=inicio,
                            fin=fin,
                            sillon_id=asignado[0].id,
                            odontologo_id=asignado[1].id,
                        )
                    )
            inicio = fin

    slots.sort(key=lambda slot: slot.inicio)
    return slots


def slot_para_inicio(slots: Sequence[Slot], inicio: datetime) -> Slot | None:
    """Buscar el slot generado que empieza exactamente en `inicio` (UTC)."""
    objetivo = _aware_utc(inicio)
    for slot in slots:
        if slot.inicio == objetivo:
            return slot
    return None


def esta_alineado(
    *,
    inicio: datetime,
    fecha: date,
    duracion_min: int,
    horarios: Sequence[_HorarioLike],
    tz: str | None = None,
) -> bool:
    """Indica si `inicio` cae en la grilla de alguna franja del día.

    No mira ocupación ni recursos: solo si el inicio es un múltiplo de la
    duración dentro de una franja activa y el turno termina antes del cierre.
    """
    if duracion_min <= 0:
        raise ValueError("duracion_min debe ser mayor a cero")

    zona = ZoneInfo(tz or settings.tz_clinica)
    duracion = timedelta(minutes=duracion_min)
    objetivo = _aware_utc(inicio)

    for horario in horarios:
        if not getattr(horario, "activo", True):
            continue
        if horario.dia_semana != fecha.weekday():
            continue
        franja_inicio = datetime.combine(fecha, horario.hora_desde, tzinfo=zona).astimezone(UTC)
        franja_fin = datetime.combine(fecha, horario.hora_hasta, tzinfo=zona).astimezone(UTC)
        cursor = franja_inicio
        while cursor + duracion <= franja_fin:
            if cursor == objetivo:
                return True
            cursor += duracion
    return False
