"""Router público de reservas: slots y alta sin login (C-05)."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.turnos import service
from app.domain.turnos.schemas import ReservaOut, ReservaPublicaIn, SlotOut, SlotsResponse
from app.infrastructure.db.session import get_session

router = APIRouter(tags=["public"])


@router.get("/slots", response_model=SlotsResponse)
async def listar_slots(
    session: Annotated[AsyncSession, Depends(get_session)],
    fecha: Annotated[date, Query(description="Fecha local de la clínica (YYYY-MM-DD)")],
    practica: Annotated[UUID, Query(description="ID de la práctica")],
) -> SlotsResponse:
    """Devolver huecos disponibles sin datos de pacientes."""
    dia = await service.obtener_slots(session, practica_id=practica, fecha=fecha)
    return SlotsResponse(
        fecha=dia.fecha,
        practica_id=dia.practica.id,
        duracion_min=dia.duracion_min,
        slots=[
            SlotOut(
                inicio=slot.inicio,
                fin=slot.fin,
                sillon_id=slot.sillon_id,
                odontologo_id=slot.odontologo_id,
            )
            for slot in dia.slots
        ],
    )


@router.post("/reservas", response_model=ReservaOut, status_code=status.HTTP_201_CREATED)
async def crear_reserva(
    payload: ReservaPublicaIn,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReservaOut:
    """Crear una reserva pública y devolver su token de gestión."""
    turno = await service.crear_turno_publico(
        session,
        nombre=payload.nombre,
        telefono=payload.telefono,
        dni=payload.dni,
        practica_id=payload.practica_id,
        inicio=payload.inicio,
    )
    return ReservaOut(
        turno_id=turno.id,
        manage_token=turno.manage_token or "",
        inicio=turno.inicio,
        fin=turno.fin,
        monto_sena=turno.monto_sena,
        estado=turno.estado,
    )
