"""Router interno de turnos con RBAC (C-05, C-06)."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.internal.catalogo import clinic_id_from_token
from app.domain.auth.dependencies import require_role
from app.domain.turnos import service
from app.domain.turnos.schemas import (
    CancelarTurnoInternoIn,
    ReprogramarTurnoInternoIn,
    TurnoGestionInternaOut,
    TurnoInternoIn,
    TurnoInternoOut,
)
from app.infrastructure.db.session import get_session

router = APIRouter(tags=["turnos"])

ROLES_ALTA = ["recepcion", "admin"]


def usuario_id_from_token(current_user: dict[str, Any]) -> UUID:
    """Extraer el `sub` del JWT como UUID para auditarlo en el log de dominio."""
    raw = current_user.get("sub")
    if raw is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin sub")
    try:
        return UUID(str(raw))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="sub inválido"
        ) from exc


@router.post("/turnos", response_model=TurnoInternoOut, status_code=status.HTTP_201_CREATED)
async def crear_turno(
    payload: TurnoInternoIn,
    current_user: Annotated[dict[str, Any], Depends(require_role(ROLES_ALTA))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TurnoInternoOut:
    """Crear un turno interno para un paciente existente, sin token público."""
    clinic_id = clinic_id_from_token(current_user)
    turno = await service.crear_turno_interno(
        session,
        clinic_id=clinic_id,
        paciente_id=payload.paciente_id,
        sillon_id=payload.sillon_id,
        odontologo_id=payload.odontologo_id,
        tipo_practica_id=payload.tipo_practica_id,
        inicio=payload.inicio,
    )
    return TurnoInternoOut.model_validate(turno)


@router.post("/turnos/{turno_id}/cancelar", response_model=TurnoGestionInternaOut)
async def cancelar_turno(
    turno_id: UUID,
    payload: CancelarTurnoInternoIn,
    current_user: Annotated[dict[str, Any], Depends(require_role(ROLES_ALTA))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TurnoGestionInternaOut:
    """Cancelar un turno de la clínica del JWT con motivo auditado."""
    clinic_id = clinic_id_from_token(current_user)
    usuario_id = usuario_id_from_token(current_user)
    turno = await service.cancelar_turno_interno(
        session,
        clinic_id=clinic_id,
        turno_id=turno_id,
        motivo=payload.motivo,
        usuario_id=usuario_id,
        confirmar_perdida_sena=payload.confirmar_perdida_sena,
    )
    return TurnoGestionInternaOut.model_validate(turno)


@router.post("/turnos/{turno_id}/reprogramar", response_model=TurnoGestionInternaOut)
async def reprogramar_turno(
    turno_id: UUID,
    payload: ReprogramarTurnoInternoIn,
    current_user: Annotated[dict[str, Any], Depends(require_role(ROLES_ALTA))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TurnoGestionInternaOut:
    """Reprogramar un turno de la clínica del JWT con motivo auditado."""
    clinic_id = clinic_id_from_token(current_user)
    usuario_id = usuario_id_from_token(current_user)
    turno = await service.reprogramar_turno_interno(
        session,
        clinic_id=clinic_id,
        turno_id=turno_id,
        nuevo_inicio=payload.nuevo_inicio,
        motivo=payload.motivo,
        usuario_id=usuario_id,
        confirmar_perdida_sena=payload.confirmar_perdida_sena,
    )
    return TurnoGestionInternaOut.model_validate(turno)
