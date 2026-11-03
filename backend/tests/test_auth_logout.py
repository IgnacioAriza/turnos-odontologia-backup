"""Tests para endpoint POST /api/auth/logout."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_logout_limpia_cookie(client: TestClient):
    """Logout debe eliminar la cookie de refresh token."""
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    # Verificar que la cookie se elimina (max-age=0 o similar)
    cookies = response.headers.get("set-cookie", "")
    assert "refresh_token=" in cookies
    assert "Max-Age=0" in cookies or "max-age=0" in cookies
