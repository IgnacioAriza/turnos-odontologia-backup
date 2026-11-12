"""Router público del catálogo de prácticas (C-06, ampliación 8b)."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clinica.repository import TipoPracticaRepository
from app.domain.clinica.schemas import PracticaPublicaOut
from app.infrastructure.db.session import get_session

router = APIRouter(tags=["public"])


@router.get("/practicas", response_model=list[PracticaPublicaOut])
async def listar_practicas(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> list[PracticaPublicaOut]:
    """Listar las prácticas reservables sin sesión ni datos internos."""
    practicas = await TipoPracticaRepository(session).list_activas_publicas()
    return [PracticaPublicaOut.model_validate(practica) for practica in practicas]
