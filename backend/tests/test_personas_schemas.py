"""Tests de los schemas Pydantic del dominio personas."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domain.personas.models import Paciente, User
from app.domain.personas.schemas import (
    PacienteCreate,
    PacienteOut,
    PacienteUpdate,
    UserCreate,
    UserOut,
    UserUpdate,
)


def test_user_create_valido() -> None:
    user = UserCreate(email="admin@clinica.com", rol="admin", password="secreto123")

    assert user.email == "admin@clinica.com"
    assert user.activo is True
    assert user.odontologo_id is None


@pytest.mark.parametrize("rol", ["paciente", "root", ""])
def test_user_create_rol_invalido(rol: str) -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="x@clinica.com", rol=rol, password="secreto123")


def test_user_create_password_corta() -> None:
    with pytest.raises(ValidationError):
        UserCreate(email="x@clinica.com", rol="odonto", password="123")


def test_user_update_todos_opcionales() -> None:
    update = UserUpdate()

    assert update.email is None
    assert update.password is None
    assert update.rol is None
    assert update.activo is None


def test_user_out_desde_orm() -> None:
    ahora = datetime.now(UTC)
    user = User(
        id=uuid4(),
        clinic_id=uuid4(),
        email="recepcion@clinica.com",
        password_hash="x",
        rol="recepcion",
        activo=True,
        is_active=True,
    )
    user.created_at = ahora
    user.updated_at = ahora

    salida = UserOut.model_validate(user)

    assert salida.id == user.id
    assert salida.clinic_id == user.clinic_id
    assert salida.email == "recepcion@clinica.com"


def test_paciente_create_permite_dni_nulo() -> None:
    paciente = PacienteCreate(nombre="Ana", telefono="+5491112345678")

    assert paciente.dni is None


def test_paciente_create_telefono_corto() -> None:
    with pytest.raises(ValidationError):
        PacienteCreate(nombre="Ana", telefono="123")


def test_paciente_update_parcial() -> None:
    update = PacienteUpdate(nombre="Ana María")

    assert update.nombre == "Ana María"
    assert update.telefono is None
    assert update.is_active is None


def test_paciente_out_desde_orm() -> None:
    ahora = datetime.now(UTC)
    paciente = Paciente(
        id=uuid4(),
        clinic_id=uuid4(),
        nombre="Ana",
        telefono="+5491112345678",
        dni=None,
        is_active=True,
    )
    paciente.created_at = ahora
    paciente.updated_at = ahora

    salida = PacienteOut.model_validate(paciente)

    assert salida.dni is None
    assert salida.nombre == "Ana"
