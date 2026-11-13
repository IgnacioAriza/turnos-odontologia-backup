"""Router interno del catálogo: prácticas y sillones (JWT)."""

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.auth.dependencies import require_role
from app.domain.clinica.models import Sillon, TipoPractica
from app.domain.clinica.repository import SillonRepository, TipoPracticaRepository
from app.domain.clinica.schemas import SillonOut, TipoPracticaOut
from app.domain.personas.models import User
from app.domain.personas.repository import UserRepository
from app.domain.personas.schemas import OdontologoOut
from app.infrastructure.db.session import get_session

router = APIRouter(tags=["catalogo"])

ROLES_LECTURA = ["recepcion", "odonto", "admin"]


def clinic_id_from_token(current_user: dict[str, Any]) -> UUID:
    """Extraer y validar `clinic_id` de las claims del JWT."""
    raw = current_user.get("clinic_id")
    if raw is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token sin clinic_id")
    try:
        return UUID(str(raw))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="clinic_id inválido"
        ) from exc


@router.get("/tipos-practica", response_model=list[TipoPracticaOut])
async def listar_tipos_practica(
    current_user: Annotated[dict[str, Any], Depends(require_role(ROLES_LECTURA))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[TipoPractica]:
    """Listar las prácticas activas de la clínica del token."""
    clinic_id = clinic_id_from_token(current_user)
    return await TipoPracticaRepository(session).list_activas(clinic_id)


@router.get("/sillones", response_model=list[SillonOut])
async def listar_sillones(
    current_user: Annotated[dict[str, Any], Depends(require_role(ROLES_LECTURA))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[Sillon]:
    """Listar los sillones activos de la clínica del token."""
    clinic_id = clinic_id_from_token(current_user)
    return await SillonRepository(session).list_activos(clinic_id)


@router.get("/odontologos", response_model=list[OdontologoOut])
async def listar_odontologos(
    current_user: Annotated[dict[str, Any], Depends(require_role(ROLES_LECTURA))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[User]:
    """Listar los odontólogos activos de la clínica para los filtros (C-07 D11)."""
    clinic_id = clinic_id_from_token(current_user)
    return await UserRepository(session).list_odontologos(clinic_id)
