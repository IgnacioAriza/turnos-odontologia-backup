"""Pydantic schemas para el dominio clínica."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ClinicBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    timezone: str = Field(default="America/Argentina/Buenos_Aires", max_length=64)
    wa_sender: str | None = Field(default=None, max_length=50)
    mp_account: str | None = Field(default=None, max_length=200)


class ClinicCreate(ClinicBase):
    pass


class ClinicUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    timezone: str | None = Field(default=None, max_length=64)
    wa_sender: str | None = Field(default=None, max_length=50)
    mp_account: str | None = Field(default=None, max_length=200)
    is_active: bool | None = None


class ClinicOut(ClinicBase):
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SillonBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    activo: bool = True


class SillonCreate(SillonBase):
    pass


class SillonUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=100)
    activo: bool | None = None


class SillonOut(SillonBase):
    id: UUID
    clinic_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BloqueoBase(BaseModel):
    paciente_id: UUID
    desde: datetime
    hasta: datetime
    motivo: str = Field(..., min_length=1, max_length=1000)


class BloqueoCreate(BloqueoBase):
    pass


class BloqueoOut(BloqueoBase):
    id: UUID
    clinic_id: UUID
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
