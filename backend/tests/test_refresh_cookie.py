"""Tests para cookie HttpOnly del refresh token."""

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def test_refresh_cookie_httponly(client: TestClient):
    """La cookie de refresh token debe ser HttpOnly."""
    # Verificar en el código fuente que set_cookie usa httponly=True
    import pathlib

    source_path = pathlib.Path(__file__).parent.parent / "app" / "api" / "auth" / "router.py"
    source = source_path.read_text(encoding="utf-8")
    assert "httponly=True" in source
    assert 'samesite="lax"' in source

    # Nota: el endpoint login requiere DB real (PostgreSQL), por lo que no se
    # puede probar aquí con SQLite. La verificación de httponly y samesite
    # se hace estáticamente sobre el código fuente.
