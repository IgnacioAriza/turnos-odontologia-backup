"""Router admin del catálogo: aranceles y cambio de % seña (solo admin)."""

from datetime import date
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.internal.catalogo import clinic_id_from_token
from app.domain.auth.dependencies import require_role
from app.domain.clinica.catalogo_service import actualizar_sena_pct, precio_efectivo
from app.domain.clinica.models import TipoPractica
from app.domain.clinica.repository import ArancelRepository, TipoPracticaRepository
from app.domain.clinica.schemas import ArancelAdminOut, SenaPctUpdate, TipoPracticaOut
from app.infrastructure.db.session import get_session

router = APIRouter(tags=["admin-catalogo"])

ADMIN_ONLY = ["admin"]


@router.get("/aranceles", response_model=list[ArancelAdminOut])
async def listar_aranceles(
    current_user: Annotated[dict[str, Any], Depends(require_role(ADMIN_ONLY))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[ArancelAdminOut]:
    """Listar todas las prácticas con su precio efectivo y % seña (solo admin).

    Incluye prácticas inactivas para que el admin vea el catálogo completo.
    """
    clinic_id = clinic_id_from_token(current_user)
    tipos = await TipoPracticaRepository(session).list_by_clinic(clinic_id)
    aranceles_repo = ArancelRepository(session)
    hoy = date.today()

    salida: list[ArancelAdminOut] = []
    for tipo in tipos:
        arancel = await aranceles_repo.get_by_tipo(tipo.id)
        salida.append(
            ArancelAdminOut(
                tipo_practica_id=tipo.id,
                nombre=tipo.nombre,
                duracion_min=tipo.duracion_min,
                precio=float(precio_efectivo(tipo, arancel, hoy)),
                sena_pct=tipo.sena_pct,
                activa=tipo.activa,
            )
        )
    return salida


@router.patch("/tipos-practica/{tipo_practica_id}/sena-pct", response_model=TipoPracticaOut)
async def cambiar_sena_pct(
    tipo_practica_id: UUID,
    payload: SenaPctUpdate,
    current_user: Annotated[dict[str, Any], Depends(require_role(ADMIN_ONLY))],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TipoPractica:
    """Actualizar el % seña de una práctica y auditar el cambio (solo admin)."""
    clinic_id = clinic_id_from_token(current_user)
    usuario_id = _usuario_id_from_token(current_user)

    tipo = await actualizar_sena_pct(
        session,
        clinic_id=clinic_id,
        tipo_practica_id=tipo_practica_id,
        nuevo_pct=payload.sena_pct,
        usuario_id=usuario_id,
    )
    if tipo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Práctica no encontrada")
    return tipo


def _usuario_id_from_token(current_user: dict[str, Any]) -> UUID | None:
    raw = current_user.get("sub")
    if raw is None:
        return None
    try:
        return UUID(str(raw))
    except ValueError:
        return None
