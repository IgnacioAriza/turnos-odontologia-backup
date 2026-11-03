"""Pydantic schemas para el dominio auth."""

from pydantic import BaseModel, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserMe(BaseModel):
    id: UUID
    email: str
    rol: str
    clinic_id: UUID
    activo: bool

    model_config = {"from_attributes": True}


class RefreshRequest(BaseModel):
    refresh_token: str
