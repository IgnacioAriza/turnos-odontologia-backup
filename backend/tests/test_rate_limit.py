"""Tests para rate limiting de login."""

from app.core.rate_limit import RATE_LIMIT_REQUESTS, check_rate_limit


def test_rate_limit_permite_hasta_5_requests():
    """Se permiten hasta 5 requests por ventana de 60s."""
    ip = "192.168.1.1"
    email = "test@clinica.com"

    for i in range(RATE_LIMIT_REQUESTS):
        allowed, _ = check_rate_limit(ip, email)
        assert allowed is True, f"Request {i + 1} debería estar permitido"


def test_rate_limit_rechaza_6to_request():
    """El 6to request en 60s debe ser rechazado."""
    ip = "192.168.1.2"
    email = "test2@clinica.com"

    for _ in range(RATE_LIMIT_REQUESTS):
        allowed, _ = check_rate_limit(ip, email)
        assert allowed is True

    allowed, retry_after = check_rate_limit(ip, email)
    assert allowed is False
    assert retry_after > 0
