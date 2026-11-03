"""Tests para claims del JWT."""

import pytest
from jose import jwt
from app.core.config import settings


def test_jwt_claims_requeridos():
    """El JWT debe contener: sub, clinic_id, rol, email, jti, type, iat, exp."""
    token = jwt.encode(
        {
            "sub": "user-123",
            "clinic_id": "clinic-123",
            "rol": "recepcion",
            "email": "recepcion@clinica.com",
            "jti": "test-jti-123",
            "type": "access",
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])

    assert "sub" in payload
    assert "clinic_id" in payload
    assert "rol" in payload
    assert "email" in payload
    assert "jti" in payload
    assert "type" in payload
    assert "iat" in payload
    assert "exp" in payload

    assert payload["type"] == "access"
    assert payload["rol"] == "recepcion"


def test_jwt_tipo_refresh():
    """El refresh token debe tener type='refresh'."""
    token = jwt.encode(
        {
            "sub": "user-123",
            "clinic_id": "clinic-123",
            "rol": "admin",
            "email": "admin@clinica.com",
            "jti": "refresh-jti",
            "type": "refresh",
        },
        settings.JWT_SECRET,
        algorithm="HS256",
    )
    payload = jwt.decode(token, settings.JWT_SECRET, algorithms=["HS256"])
    assert payload["type"] == "refresh"
