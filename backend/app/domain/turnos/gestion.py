"""Reglas puras de gestión de turnos: ventana de 12 horas y estados (C-06).

La ventana se evalúa sobre instantes UTC. Un `datetime` naive se interpreta en
la zona de la clínica, que Argentina no cambia por horario de verano hoy pero
el cálculo no asume un offset fijo.
"""

from datetime import UTC, datetime, timedelta, tzinfo
from zoneinfo import ZoneInfo

VENTANA_GESTION = timedelta(hours=12)

ESTADOS_GESTIONABLES = ("pendiente_sena", "confirmado", "reprogramado")
ESTADOS_FINALES = ("cancelado", "completado", "ausente")

# Códigos estables del canal público (design.md D4). El frontend decide qué
# diálogo mostrar sin parsear el mensaje.
CODIGO_TOKEN_INVALIDO = "token_invalido"
CODIGO_TURNO_NO_ENCONTRADO = "turno_no_encontrado"
CODIGO_ESTADO_NO_GESTIONABLE = "estado_no_gestionable"
CODIGO_REQUIERE_CONFIRMACION = "requiere_confirmacion"
CODIGO_REQUIERE_NUEVA_SENA = "requiere_nueva_sena"
CODIGO_SOLAPE = "solape"
CODIGO_SLOT_INVALIDO = "slot_invalido"
CODIGO_RATE_LIMITED = "rate_limited"


def _zona(tz: str | tzinfo) -> tzinfo:
    return ZoneInfo(tz) if isinstance(tz, str) else tz


def _aware_utc(value: datetime, zona: tzinfo) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=zona).astimezone(UTC)
    return value.astimezone(UTC)


def dentro_de_ventana(
    inicio: datetime, now: datetime, tz: str | tzinfo = "America/Argentina/Buenos_Aires"
) -> bool:
    """Indica si faltan al menos 12 horas para el inicio del turno.

    El límite exacto de 12 horas cuenta como dentro de la ventana.
    """
    zona = _zona(tz)
    return _aware_utc(inicio, zona) - _aware_utc(now, zona) >= VENTANA_GESTION


def es_gestionable(estado: str) -> bool:
    """Solo los estados vigentes admiten cancelación o reprogramación."""
    return estado in ESTADOS_GESTIONABLES


__all__ = [
    "CODIGO_ESTADO_NO_GESTIONABLE",
    "CODIGO_RATE_LIMITED",
    "CODIGO_REQUIERE_CONFIRMACION",
    "CODIGO_REQUIERE_NUEVA_SENA",
    "CODIGO_SLOT_INVALIDO",
    "CODIGO_SOLAPE",
    "CODIGO_TOKEN_INVALIDO",
    "CODIGO_TURNO_NO_ENCONTRADO",
    "ESTADOS_FINALES",
    "ESTADOS_GESTIONABLES",
    "VENTANA_GESTION",
    "dentro_de_ventana",
    "es_gestionable",
]
