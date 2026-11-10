"""Pydantic schemas del motor de turnos (C-05)."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class SlotOut(BaseModel):
    """Hueco disponible, sin datos de pacientes."""

    inicio: datetime
    fin: datetime
    sillon_id: UUID
    odontologo_id: UUID


class SlotsResponse(BaseModel):
    fecha: date
    practica_id: UUID
    duracion_min: int
    slots: list[SlotOut]


class ReservaPublicaIn(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    telefono: str = Field(..., min_length=5, max_length=50)
    dni: str | None = Field(default=None, max_length=20)
    practica_id: UUID
    inicio: datetime


class ReservaOut(BaseModel):
    turno_id: UUID
    manage_token: str
    inicio: datetime
    fin: datetime
    monto_sena: Decimal
    estado: str


class TurnoInternoIn(BaseModel):
    paciente_id: UUID
    sillon_id: UUID
    odontologo_id: UUID
    tipo_practica_id: UUID
    inicio: datetime


class TurnoInternoOut(BaseModel):
    id: UUID
    paciente_id: UUID
    sillon_id: UUID
    odontologo_id: UUID
    tipo_practica_id: UUID
    inicio: datetime
    fin: datetime
    estado: str
    monto_sena: Decimal
    manage_token: str | None = None

    model_config = {"from_attributes": True}


__all__ = [
    "ReservaOut",
    "ReservaPublicaIn",
    "SlotOut",
    "SlotsResponse",
    "TurnoInternoIn",
    "TurnoInternoOut",
]
