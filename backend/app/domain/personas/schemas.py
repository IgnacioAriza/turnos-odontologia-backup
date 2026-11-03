"""Pydantic schemas para el dominio personas."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    rol: str = Field(..., pattern="^(recepcion|odonto|admin)$")
    activo: bool = True
    odontologo_id: Optional[UUID] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=128)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
    rol: Optional[str] = Field(default=None, pattern="^(recepcion|odonto|admin)$")
    activo: Optional[bool] = None
    odontologo_id: Optional[UUID] = None


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
    nombre: Optional[str] = Field(default=None, min_length=1, max_length=200)
    telefono: Optional[str] = Field(default=None, min_length=8, max_length=50)
    dni: Optional[str] = Field(default=None, min_length=6, max_length=20)
    is_active: Optional[bool] = None


class PacienteOut(PacienteBase):
    id: UUID
    clinic_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
