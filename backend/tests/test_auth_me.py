"""Tests para endpoint GET /api/auth/me."""

import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from jose import jwt
from app.core.config import settings


@pytest.fixture
def client():
    return TestClient(create_app())


def test_me_sin_token_retorna_401(client: TestClient):
    """GET /me sin token debe retornar 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_con_token_valido(client: TestClient):
    """GET /me con token válido retorna datos del usuario."""
    token = jwt.encode(
        {
            "sub": "user-123",
            "clinic_id": "clinic-123",
            "rol": "admin",
            "email": "admin@clinica.com",
            "jti": "test-jti",
            "type": "access",
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin@clinica.com"
    assert data["rol"] == "admin"
