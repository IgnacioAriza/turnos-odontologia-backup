"""Pydantic schemas del motor de turnos (C-05)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

MotivoGestion = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)
]


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


class PracticaResumenOut(BaseModel):
    id: UUID
    nombre: str
    duracion_min: int


class GestionTurnoOut(BaseModel):
    """Vista pública del turno: sin `manage_token` ni datos de otros pacientes."""

    turno_id: UUID
    estado: str
    inicio: datetime
    fin: datetime
    practica: PracticaResumenOut
    monto_sena: Decimal
    sena_perdida: bool
    reprogramaciones_count: int
    reprogramaciones_restantes: int
    dentro_de_ventana: bool


class CancelarGestionIn(BaseModel):
    manage_token: str = Field(..., min_length=10, max_length=128)
    confirmar_perdida_sena: bool = False


class ReprogramarGestionIn(CancelarGestionIn):
    nuevo_inicio: datetime


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


class CancelarTurnoInternoIn(BaseModel):
    """Cancelación por el canal interno: el motivo es obligatorio y auditado."""

    motivo: MotivoGestion
    confirmar_perdida_sena: bool = False


class ReprogramarTurnoInternoIn(CancelarTurnoInternoIn):
    nuevo_inicio: datetime


class TurnoGestionInternaOut(BaseModel):
    """Vista interna de un turno gestionado: nunca expone `manage_token`."""

    id: UUID
    paciente_id: UUID
    sillon_id: UUID
    odontologo_id: UUID
    tipo_practica_id: UUID
    inicio: datetime
    fin: datetime
    estado: str
    monto_sena: Decimal
    sena_perdida: bool
    reprogramaciones_count: int
    reprogramado_de_id: UUID | None = None

    model_config = {"from_attributes": True}


__all__ = [
    "CancelarTurnoInternoIn",
    "ReprogramarTurnoInternoIn",
    "ReservaOut",
    "ReservaPublicaIn",
    "SlotOut",
    "SlotsResponse",
    "TurnoGestionInternaOut",
    "TurnoInternoIn",
    "TurnoInternoOut",
]
