"""Router interno de pacientes: búsqueda para el alta de la agenda (C-07).

El alta interna exige `paciente_id`; recepción y admin necesitan encontrar al
paciente existente sin conocer su UUID. La búsqueda queda confinada a la clínica
del JWT y el odontólogo no la usa porque no tiene alta.
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.internal.catalogo import clinic_id_from_token
from app.domain.auth.dependencies import require_role
from app.domain.personas.models import Paciente
from app.domain.personas.repository import PacienteRepository
from app.domain.personas.schemas import PacienteBusquedaOut
from app.infrastructure.db.session import get_session

router = APIRouter(tags=["pacientes"])

ROLES_ALTA = ["recepcion", "admin"]


@router.get("/pacientes", response_model=list[PacienteBusquedaOut])
async def buscar_pacientes(
    current_user: Annotated[dict[str, Any], Depends(require_role(ROLES_ALTA))],
    session: Annotated[AsyncSession, Depends(get_session)],
    q: Annotated[
        str,
        Query(
            min_length=2,
            max_length=100,
            description="Nombre, teléfono o DNI (parcial, sin distinguir mayúsculas)",
        ),
    ],
) -> list[Paciente]:
    """Buscar pacientes activos de la clínica del JWT (máximo 20, por nombre)."""
    clinic_id = clinic_id_from_token(current_user)
    return await PacienteRepository(session).buscar(clinic_id, q)
