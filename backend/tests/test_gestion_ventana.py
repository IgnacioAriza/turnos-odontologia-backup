"""Tests de la ventana de gestión de 12 horas (C-06, tarea 3.1)."""

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.domain.turnos.gestion import (
    ESTADOS_FINALES,
    ESTADOS_GESTIONABLES,
    VENTANA_GESTION,
    dentro_de_ventana,
    es_gestionable,
)

AR = ZoneInfo("America/Argentina/Buenos_Aires")


def test_ventana_son_12_horas() -> None:
    assert VENTANA_GESTION == timedelta(hours=12)


def test_limite_exacto_de_12_horas_se_acepta() -> None:
    now = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    inicio = now + timedelta(hours=12)

    assert dentro_de_ventana(inicio, now, AR) is True


def test_un_segundo_menos_de_12_horas_se_rechaza() -> None:
    now = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    inicio = now + timedelta(hours=12) - timedelta(seconds=1)

    assert dentro_de_ventana(inicio, now, AR) is False


def test_turno_en_el_pasado_queda_fuera_de_ventana() -> None:
    now = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    inicio = now - timedelta(minutes=1)

    assert dentro_de_ventana(inicio, now, AR) is False


def test_inicio_naive_se_interpreta_en_la_zona_de_la_clinica() -> None:
    """23:00 en Buenos Aires = 02:00 UTC del día siguiente → 16 horas."""
    now = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    inicio = datetime(2026, 1, 5, 23, 0)

    assert dentro_de_ventana(inicio, now, AR) is True


def test_now_naive_se_interpreta_en_la_zona_de_la_clinica() -> None:
    now = datetime(2026, 1, 5, 7, 0)
    inicio = datetime(2026, 1, 5, 18, 0, tzinfo=UTC)

    # 07:00 en Buenos Aires = 10:00 UTC → inicio a 8 horas.
    assert dentro_de_ventana(inicio, now, AR) is False


def test_respeta_la_zona_de_la_clinica_recibida() -> None:
    """La misma entrada naive cambia de resultado según la zona de la clínica."""
    now = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    inicio = datetime(2026, 1, 5, 21, 0)

    assert dentro_de_ventana(inicio, now, ZoneInfo("America/New_York")) is True
    assert dentro_de_ventana(inicio, now, AR) is True
    assert dentro_de_ventana(inicio, now, UTC) is False


def test_acepta_zona_como_string() -> None:
    now = datetime(2026, 1, 5, 10, 0, tzinfo=UTC)
    inicio = now + timedelta(hours=13)

    assert dentro_de_ventana(inicio, now, "America/Argentina/Buenos_Aires") is True


@pytest.mark.parametrize("estado", ["pendiente_sena", "confirmado", "reprogramado"])
def test_estados_gestionables(estado: str) -> None:
    assert es_gestionable(estado) is True
    assert estado in ESTADOS_GESTIONABLES


@pytest.mark.parametrize("estado", ["cancelado", "completado", "ausente"])
def test_estados_finales_no_son_gestionables(estado: str) -> None:
    assert es_gestionable(estado) is False
    assert estado in ESTADOS_FINALES


def test_estado_desconocido_no_es_gestionable() -> None:
    assert es_gestionable("inventado") is False
