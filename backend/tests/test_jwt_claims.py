"""Tests para claims del JWT."""

from jose import jwt

from app.core.config import settings


def test_jwt_claims_requeridos():
    """El JWT debe contener: sub, clinic_id, rol, email, jti, type, iat, exp."""
    import datetime

    now = datetime.datetime.now(datetime.UTC)
    token = jwt.encode(
        {
            "sub": "user-123",
            "clinic_id": "clinic-123",
            "rol": "recepcion",
            "email": "recepcion@clinica.com",
            "jti": "test-jti-123",
            "type": "access",
            "iat": now,
            "exp": now + datetime.timedelta(minutes=30),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])

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
    import datetime

    now = datetime.datetime.now(datetime.UTC)
    token = jwt.encode(
        {
            "sub": "user-123",
            "clinic_id": "clinic-123",
            "rol": "admin",
            "email": "admin@clinica.com",
            "jti": "refresh-jti",
            "type": "refresh",
            "iat": now,
            "exp": now + datetime.timedelta(days=7),
        },
        settings.jwt_secret,
        algorithm="HS256",
    )
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    assert payload["type"] == "refresh"
