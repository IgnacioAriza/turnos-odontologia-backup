"""Tests para endpoint POST /api/auth/refresh (rotación de refresh token)."""

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
def test_refresh_rotation_invalida_anterior(client: TestClient, db_session):
    """Rotación de refresh token invalida el anterior."""
    clinic = Clinic(nombre="Test Clinic", timezone="America/Argentina/Buenos_Aires")
    db_session.add(clinic)
    db_session.flush()

    user = User(
        clinic_id=clinic.id,
        email="refresh@clinica.com",
        password_hash=hash_password("Password123!"),
        rol="admin",
        activo=True,
    )
    db_session.add(user)
    db_session.commit()

    # Login para obtener tokens
    response = client.post(
        "/api/auth/login",
        json={"email": "refresh@clinica.com", "password": "Password123!"},
    )
    assert response.status_code == 200
    tokens = response.json()
    old_refresh = tokens["refresh_token"]

    # Usar refresh token para rotar
    response2 = client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": old_refresh},
    )
    assert response2.status_code == 200
    new_tokens = response2.json()
    assert new_tokens["refresh_token"] != old_refresh

    # El refresh token antiguo ya no debe funcionar
    response3 = client.post(
        "/api/auth/refresh",
        cookies={"refresh_token": old_refresh},
    )
    assert response3.status_code == 401
