"""Pydantic schemas para el dominio personas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    email: EmailStr
    rol: str = Field(..., pattern="^(recepcion|odonto|admin)$")
    activo: bool = True
    odontologo_id: UUID | None = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=6, max_length=128)
    rol: str | None = Field(default=None, pattern="^(recepcion|odonto|admin)$")
    activo: bool | None = None
    odontologo_id: UUID | None = None


class UserOut(UserBase):
    id: UUID
    clinic_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PacienteBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    telefono: str = Field(..., min_length=8, max_length=50)
    dni: str = Field(..., min_length=6, max_length=20)


class PacienteCreate(PacienteBase):
    pass


class PacienteUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=200)
    telefono: str | None = Field(default=None, min_length=8, max_length=50)
    dni: str | None = Field(default=None, min_length=6, max_length=20)
    is_active: bool | None = None


class PacienteOut(PacienteBase):
    id: UUID
    clinic_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
