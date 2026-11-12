"""Puerto de recordatorios de turnos (C-06).

C-10 reemplaza `NoOpRecordatorio` por la implementación real de Redis/Twilio.
El dominio de turnos solo conoce el puerto, así que cancelar o reprogramar
nunca depende de que la capa de notificaciones exista todavía.
"""

from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from app.core.logging import get_logger

logger = get_logger(__name__)


@runtime_checkable
class RecordatorioPort(Protocol):
    """Señales que el motor de turnos emite hacia notificaciones."""

    async def cancelar(self, turno_id: UUID) -> None: ...

    async def reprogramar(self, turno_id: UUID, inicio: datetime) -> None: ...


class NoOpRecordatorio:
    """Implementación de v1.0: registra la señal y no envía nada."""

    async def cancelar(self, turno_id: UUID) -> None:
        logger.info("recordatorio_cancelado", turno_id=str(turno_id))

    async def reprogramar(self, turno_id: UUID, inicio: datetime) -> None:
        logger.info(
            "recordatorio_reprogramado",
            turno_id=str(turno_id),
            nuevo_inicio=inicio.isoformat(),
        )


__all__ = ["NoOpRecordatorio", "RecordatorioPort"]
