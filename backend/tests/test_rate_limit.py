"""Tests del rate limiter parametrizable y del login (C-06, tarea 6.6)."""

from app.core.rate_limit import (
    RATE_LIMIT_REQUESTS,
    RATE_LIMIT_WINDOW,
    check_login_rate_limit,
    check_rate_limit,
    reset_rate_limit_store,
)


def test_login_permite_hasta_5_requests():
    """Se permiten hasta 5 requests por ventana de 60s."""
    ip = "192.168.1.1"
    email = "test@clinica.com"

    for i in range(RATE_LIMIT_REQUESTS):
        allowed, _ = check_login_rate_limit(ip, email)
        assert allowed is True, f"Request {i + 1} debería estar permitido"


def test_login_rechaza_6to_request():
    """El 6to request en 60s debe ser rechazado."""
    ip = "192.168.1.2"
    email = "test2@clinica.com"

    for _ in range(RATE_LIMIT_REQUESTS):
        allowed, _ = check_login_rate_limit(ip, email)
        assert allowed is True

    allowed, retry_after = check_login_rate_limit(ip, email)
    assert allowed is False
    assert retry_after > 0


def test_login_conserva_la_ventana_de_60s():
    assert RATE_LIMIT_WINDOW == 60
    assert RATE_LIMIT_REQUESTS == 5


def test_generico_respeta_el_limite_recibido() -> None:
    for _ in range(3):
        allowed, _ = check_rate_limit("gestion_ip", "ip-a", limit=3, window=60)
        assert allowed is True

    allowed, retry_after = check_rate_limit("gestion_ip", "ip-a", limit=3, window=60)
    assert allowed is False
    assert retry_after > 0


def test_scopes_y_keys_son_independientes() -> None:
    for _ in range(2):
        check_rate_limit("gestion_ip", "ip-b", limit=2, window=60)
    assert check_rate_limit("gestion_ip", "ip-b", limit=2, window=60)[0] is False

    assert check_rate_limit("gestion_token", "ip-b", limit=2, window=60)[0] is True
    assert check_rate_limit("gestion_ip", "ip-c", limit=2, window=60)[0] is True


def test_reset_limpia_el_almacen() -> None:
    for _ in range(2):
        check_rate_limit("gestion_ip", "ip-d", limit=2, window=60)
    assert check_rate_limit("gestion_ip", "ip-d", limit=2, window=60)[0] is False

    reset_rate_limit_store()

    assert check_rate_limit("gestion_ip", "ip-d", limit=2, window=60)[0] is True
