"""Router interno de turnos con RBAC (C-05)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.internal.catalogo import clinic_id_from_token
from app.domain.auth.dependencies import require_role
from app.domain.turnos import service
from app.domain.turnos.schemas import TurnoInternoIn, TurnoInternoOut
from app.infrastructure.db.session import get_session

router = APIRouter(tags=["turnos"])

ROLES_ALTA = ["recepcion", "admin"]


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
