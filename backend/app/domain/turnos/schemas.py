"""Pydantic schemas del motor de turnos (C-05)."""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Literal
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
    # C-07: excepción auditada al bloqueo por ausentismo. Opcional; el dominio
    # valida que no sea vacío y la registra en `excepciones_bloqueo`.
    motivo_excepcion: str | None = Field(default=None, max_length=500)


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


class AgendaPacienteOut(BaseModel):
    """Paciente en la agenda: solo identidad, sin datos de contacto."""

    id: UUID
    nombre: str


class AgendaPracticaOut(BaseModel):
    id: UUID
    nombre: str


class AgendaSillonOut(BaseModel):
    id: UUID
    nombre: str


class AgendaOdontologoOut(BaseModel):
    id: UUID
    email: str


class AgendaTurnoOut(BaseModel):
    """Turno de la agenda con hora local de la clínica (C-07 D2)."""

    id: UUID
    inicio: datetime
    fin: datetime
    estado: str
    paciente: AgendaPacienteOut
    practica: AgendaPracticaOut
    sillon: AgendaSillonOut
    odontologo: AgendaOdontologoOut


class AgendaOut(BaseModel):
    vista: str
    desde: datetime
    hasta: datetime
    turnos: list[AgendaTurnoOut]


class PanelPacienteOut(BaseModel):
    """Paciente en el panel: contacto y contador de faltas para el aviso de bloqueo."""

    id: UUID
    nombre: str
    telefono: str
    faltas_count: int
    bloqueado_hasta: datetime | None = None


class PanelTurnoOut(BaseModel):
    """Turno operable de la jornada con el estado de seña derivado (C-07 D4)."""

    id: UUID
    inicio: datetime
    fin: datetime
    estado: str
    estado_sena: str
    monto_sena: Decimal
    paciente: PanelPacienteOut
    practica: AgendaPracticaOut
    sillon: AgendaSillonOut
    odontologo: AgendaOdontologoOut


class ResumenPanelOut(BaseModel):
    total: int
    pendientes_sena: int
    confirmados: int
    completados: int
    ausentes: int


class PanelDiaOut(BaseModel):
    fecha: date
    turnos: list[PanelTurnoOut]
    resumen: ResumenPanelOut


class MarcarTurnoIn(BaseModel):
    """Único contrato de marcado del panel: llegada o ausencia."""

    estado: Literal["completado", "ausente"]


__all__ = [
    "AgendaOdontologoOut",
    "AgendaOut",
    "AgendaPacienteOut",
    "AgendaPracticaOut",
    "AgendaSillonOut",
    "AgendaTurnoOut",
    "CancelarTurnoInternoIn",
    "MarcarTurnoIn",
    "PanelDiaOut",
    "PanelPacienteOut",
    "PanelTurnoOut",
    "ReprogramarTurnoInternoIn",
    "ReservaOut",
    "ReservaPublicaIn",
    "ResumenPanelOut",
    "SlotOut",
    "SlotsResponse",
    "TurnoGestionInternaOut",
    "TurnoInternoIn",
    "TurnoInternoOut",
]
