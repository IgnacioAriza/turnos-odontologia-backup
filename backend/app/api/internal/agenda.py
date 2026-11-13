"""Router interno de la agenda operativa multi-sillón (C-07).

`GET /api/internal/agenda` es la lectura de la agenda día/semana. El
confinamiento del odontólogo es server-side y silencioso (design D3): se fuerza
su `sub` como filtro aunque el query pida otro odontólogo.
"""

from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.internal.catalogo import clinic_id_from_token
from app.domain.auth.dependencies import require_odonto_confinement, require_role
from app.domain.turnos.models import Turno
from app.domain.turnos.schemas import (
    AgendaOdontologoOut,
    AgendaOut,
    AgendaPacienteOut,
    AgendaPracticaOut,
    AgendaSillonOut,
    AgendaTurnoOut,
)
from app.domain.turnos.service import AgendaService
from app.infrastructure.db.session import get_session

router = APIRouter(tags=["agenda"])

ROLES_AGENDA = ["recepcion", "odonto", "admin"]

VistaAgenda = Literal["dia", "semana"]
EstadoAgenda = Literal[
    "pendiente_sena", "confirmado", "cancelado", "reprogramado", "completado", "ausente"
]


def _uuid_confinado(raw: str | None) -> UUID | None:
    """Convertir el `sub` del odontólogo confinado, rechazando un JWT corrupto."""
    if raw is None:
        return None
    try:
        return UUID(raw)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="sub inválido"
        ) from exc


def _a_zona(value: datetime, zona: ZoneInfo) -> datetime:
    """Normalizar a la zona de la clínica; SQLite devuelve datetimes naive."""
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value
    return aware.astimezone(zona)


def _turno_out(turno: Turno, zona: ZoneInfo) -> AgendaTurnoOut:
    return AgendaTurnoOut(
        id=turno.id,
        inicio=_a_zona(turno.inicio, zona),
        fin=_a_zona(turno.fin, zona),
        estado=turno.estado,
        paciente=AgendaPacienteOut(id=turno.paciente.id, nombre=turno.paciente.nombre),
        practica=AgendaPracticaOut(id=turno.tipo_practica.id, nombre=turno.tipo_practica.nombre),
        sillon=AgendaSillonOut(id=turno.sillon.id, nombre=turno.sillon.nombre),
        odontologo=AgendaOdontologoOut(id=turno.odontologo.id, email=turno.odontologo.email),
    )


@router.get("/agenda", response_model=AgendaOut)
async def listar_agenda(
    current_user: Annotated[dict[str, Any], Depends(require_role(ROLES_AGENDA))],
    confinado: Annotated[str | None, Depends(require_odonto_confinement)],
    session: Annotated[AsyncSession, Depends(get_session)],
    vista: Annotated[VistaAgenda, Query(description="Vista día o semana ISO")] = "dia",
    fecha: Annotated[date | None, Query(description="Día de referencia; hoy por defecto")] = None,
    sillon: Annotated[UUID | None, Query(description="Filtrar por sillón")] = None,
    odontologo: Annotated[
        UUID | None, Query(description="Filtrar por odontólogo (ignorado si el rol es odonto)")
    ] = None,
    estado: Annotated[
        EstadoAgenda | None, Query(description="Filtrar por estado; excluye cancelado por defecto")
    ] = None,
) -> AgendaOut:
    """Listar los turnos de la agenda de la clínica del JWT."""
    clinic_id = clinic_id_from_token(current_user)
    resultado = await AgendaService(session).listar(
        clinic_id=clinic_id,
        vista=vista,
        fecha=fecha,
        sillon_id=sillon,
        odontologo_id=odontologo,
        estado=estado,
        odontologo_confinado=_uuid_confinado(confinado),
    )
    return AgendaOut(
        vista=resultado.vista,
        desde=_a_zona(resultado.desde, resultado.zona),
        hasta=_a_zona(resultado.hasta, resultado.zona),
        turnos=[_turno_out(turno, resultado.zona) for turno in resultado.turnos],
    )
