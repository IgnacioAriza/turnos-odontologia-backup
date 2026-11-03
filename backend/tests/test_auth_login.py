"""Tests para endpoint POST /api/auth/login."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.security import hash_password
from app.domain.clinica.models import Clinic
from app.domain.personas.models import User
from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


@pytest.mark.skipif(
    "sqlite" in settings.database_url,
    reason="Requires PostgreSQL for database operations",
)
def test_login_correcto(client: TestClient, db_session):
    """Login con credenciales válidas retorna 200 + tokens."""
    clinic = Clinic(nombre="Test Clinic", timezone="America/Argentina/Buenos_Aires")
    db_session.add(clinic)
    db_session.flush()

    user = User(
        clinic_id=clinic.id,
        email="test@clinica.com",
        password_hash=hash_password("Password123!"),
        rol="recepcion",
        activo=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "test@clinica.com", "password": "Password123!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.skipif(
    "sqlite" in settings.database_url,
    reason="Requires PostgreSQL for database operations",
)
def test_login_contraseña_incorrecta(client: TestClient, db_session):
    """Login con contraseña incorrecta retorna 401."""
    clinic = Clinic(nombre="Test Clinic", timezone="America/Argentina/Buenos_Aires")
    db_session.add(clinic)
    db_session.flush()

    user = User(
        clinic_id=clinic.id,
        email="test@clinica.com",
        password_hash=hash_password("Password123!"),
        rol="recepcion",
        activo=True,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "test@clinica.com", "password": "WrongPassword!"},
    )
    assert response.status_code == 401


@pytest.mark.skipif(
    "sqlite" in settings.database_url,
    reason="Requires PostgreSQL for database operations",
)
def test_login_usuario_inexistente(client: TestClient):
    """Login con email inexistente retorna 401."""
    response = client.post(
        "/api/auth/login",
        json={"email": "noexiste@clinica.com", "password": "Password123!"},
    )
    assert response.status_code == 401


@pytest.mark.skipif(
    "sqlite" in settings.database_url,
    reason="Requires PostgreSQL for database operations",
)
def test_login_usuario_inactivo(client: TestClient, db_session):
    """Login con usuario inactivo retorna 401."""
    clinic = Clinic(nombre="Test Clinic", timezone="America/Argentina/Buenos_Aires")
    db_session.add(clinic)
    db_session.flush()

    user = User(
        clinic_id=clinic.id,
        email="inactivo@clinica.com",
        password_hash=hash_password("Password123!"),
        rol="recepcion",
        activo=False,
    )
    db_session.add(user)
    db_session.commit()

    response = client.post(
        "/api/auth/login",
        json={"email": "inactivo@clinica.com", "password": "Password123!"},
    )
    assert response.status_code == 401
