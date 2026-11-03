"""Tests para endpoint GET /api/auth/me."""

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import settings
from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_me_sin_token_retorna_401(client: TestClient):
    """GET /me sin token debe retornar 401."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_me_con_token_valido(client: TestClient):
    """GET /me con token válido retorna datos del usuario."""
    import datetime
    import uuid

    now = datetime.datetime.now(datetime.UTC)
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "clinic_id": str(uuid.uuid4()),
            "rol": "admin",
            "email": "admin@clinica.com",
            "jti": str(uuid.uuid4()),
            "type": "access",
            "iat": now,
            "exp": now + datetime.timedelta(minutes=30),
        },
        settings.jwt_secret,
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
