"""Router interno del panel del día y del marcado de llegadas/ausencias (C-07).

`GET /api/internal/panel/dia` lista la jornada y `PATCH
/api/internal/panel/turnos/{id}` registra la llegada o la ausencia. El bloqueo
por la segunda falta vive en el servicio de dominio (design D5/D6).
"""

from datetime import UTC, date, datetime
from typing import Annotated, Any
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.internal.catalogo import clinic_id_from_token
from app.api.internal.turnos import usuario_id_from_token
from app.core.config import settings
from app.domain.auth.dependencies import require_odonto_confinement, require_role
from app.domain.clinica.repository import ClinicRepository
from app.domain.turnos import service
from app.domain.turnos.gestion import estado_sena
from app.domain.turnos.models import Turno
from app.domain.turnos.schemas import (
    AgendaOdontologoOut,
    AgendaPracticaOut,
    AgendaSillonOut,
    MarcarTurnoIn,
    PanelDiaOut,
    PanelPacienteOut,
    PanelTurnoOut,
    ResumenPanelOut,
)
from app.domain.turnos.service import PanelService
from app.infrastructure.db.session import get_session

router = APIRouter(tags=["panel"])

ROLES_PANEL = ["recepcion", "admin", "odonto"]


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


def _turno_out(turno: Turno, zona: ZoneInfo) -> PanelTurnoOut:
    return PanelTurnoOut(
        id=turno.id,
        inicio=_a_zona(turno.inicio, zona),
        fin=_a_zona(turno.fin, zona),
        estado=turno.estado,
        estado_sena=estado_sena(
            monto_sena=turno.monto_sena,
            sena_perdida=turno.sena_perdida,
            estado=turno.estado,
        ),
        monto_sena=turno.monto_sena,
        paciente=PanelPacienteOut(
            id=turno.paciente.id,
            nombre=turno.paciente.nombre,
            telefono=turno.paciente.telefono,
        ),
        practica=AgendaPracticaOut(id=turno.tipo_practica.id, nombre=turno.tipo_practica.nombre),
        sillon=AgendaSillonOut(id=turno.sillon.id, nombre=turno.sillon.nombre),
        odontologo=AgendaOdontologoOut(id=turno.odontologo.id, email=turno.odontologo.email),
    )


async def _zona_de_clinica(session: AsyncSession, clinic_id: UUID) -> ZoneInfo:
    clinic = await ClinicRepository(session).get(clinic_id)
    timezone = clinic.timezone if clinic is not None and clinic.timezone else settings.tz_clinica
    return ZoneInfo(timezone)


@router.get("/panel/dia", response_model=PanelDiaOut)
async def panel_dia(
    current_user: Annotated[dict[str, Any], Depends(require_role(ROLES_PANEL))],
    confinado: Annotated[str | None, Depends(require_odonto_confinement)],
    session: Annotated[AsyncSession, Depends(get_session)],
    fecha: Annotated[date | None, Query(description="Día a operar; hoy por defecto")] = None,
) -> PanelDiaOut:
    """Listar los turnos operables de la jornada con su resumen."""
    clinic_id = clinic_id_from_token(current_user)
    resultado = await PanelService(session).listar(
        clinic_id=clinic_id,
        fecha=fecha,
        odontologo_confinado=_uuid_confinado(confinado),
    )
    return PanelDiaOut(
        fecha=resultado.fecha,
        turnos=[_turno_out(turno, resultado.zona) for turno in resultado.turnos],
        resumen=ResumenPanelOut(
            total=resultado.resumen.total,
            pendientes_sena=resultado.resumen.pendientes_sena,
            confirmados=resultado.resumen.confirmados,
            completados=resultado.resumen.completados,
            ausentes=resultado.resumen.ausentes,
        ),
    )


@router.patch("/panel/turnos/{turno_id}", response_model=PanelTurnoOut)
async def marcar_turno(
    turno_id: UUID,
    payload: MarcarTurnoIn,
    current_user: Annotated[dict[str, Any], Depends(require_role(ROLES_PANEL))],
    confinado: Annotated[str | None, Depends(require_odonto_confinement)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> PanelTurnoOut:
    """Marcar un turno como `completado` o `ausente` (idempotente por destino)."""
    clinic_id = clinic_id_from_token(current_user)
    usuario_id = usuario_id_from_token(current_user)
    turno = await service.marcar_turno_panel(
        session,
        clinic_id=clinic_id,
        turno_id=turno_id,
        destino=payload.estado,
        usuario_id=usuario_id,
        odontologo_confinado=_uuid_confinado(confinado),
    )
    zona = await _zona_de_clinica(session, clinic_id)
    return _turno_out(turno, zona)
