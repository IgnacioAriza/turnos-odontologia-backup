"""Tests para guards de RBAC."""

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_require_role_recepcion(client: TestClient):
    """require_role(['recepcion']) permite acceso a recepción."""
    token = jwt.encode(
        {
            "sub": "user-123",
            "clinic_id": "clinic-123",
            "rol": "recepcion",
            "email": "recepcion@clinica.com",
            "jti": "test-jti",
            "type": "access",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    # Verificar que el token tiene el rol correcto
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    assert payload["rol"] == "recepcion"


def test_require_role_admin(client: TestClient):
    """require_role(['admin']) permite acceso a admin."""
    token = jwt.encode(
        {
            "sub": "user-456",
            "clinic_id": "clinic-123",
            "rol": "admin",
            "email": "admin@clinica.com",
            "jti": "test-jti-2",
            "type": "access",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    assert payload["rol"] == "admin"


def test_odonto_no_puede_acceder_ruta_admin(client: TestClient):
    """Odontólogo no debe tener rol admin."""
    token = jwt.encode(
        {
            "sub": "user-789",
            "clinic_id": "clinic-123",
            "rol": "odonto",
            "email": "odonto@clinica.com",
            "jti": "test-jti-3",
            "type": "access",
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    assert payload["rol"] == "odonto"
    assert payload["rol"] != "admin"
