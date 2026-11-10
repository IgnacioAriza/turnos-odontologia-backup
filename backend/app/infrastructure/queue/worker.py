"""Worker de background: barrido de turnos sin seña vencidos (C-05).

Cada 30 segundos marca como `cancelado` los turnos `pendiente_sena` cuyo
`expira_at` ya pasó. El barrido es idempotente y no depende de Redis: si el
worker no corre, `obtener_slots` y las altas también liberan vencidos antes de
calcular, así que la corrección se mantiene.
"""

import asyncio
import signal
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import configure_logging, get_logger
from app.domain.turnos import service

configure_logging()
logger = get_logger(__name__)

INTERVALO_BARRIDO_SEG = 30


async def barrido_una_vez(
    *, now: datetime | None = None, session: AsyncSession | None = None
) -> int:
    """Expirar pendientes una vez y devolver cuántos turnos se cancelaron.

    Si se pasa `session` (tests, tareas manuales) se usa tal cual y no se
    commitea; si no, abre una sesión propia y persiste el resultado.
    """
    if session is not None:
        return await service.expirar_pendientes(session, now=now)

    from app.infrastructure.db.session import async_session

    async with async_session() as nueva:
        cantidad = await service.expirar_pendientes(nueva, now=now)
        await nueva.commit()
        return cantidad


async def process_jobs() -> None:
    logger.info("worker_started", intervalo_seg=INTERVALO_BARRIDO_SEG)
    while True:
        try:
            cantidad = await barrido_una_vez()
            if cantidad:
                logger.info("turnos_expirados", cantidad=cantidad)
        except Exception as exc:  # noqa: BLE001
            logger.error("barrido_error", error=str(exc), exc_info=True)
        await asyncio.sleep(INTERVALO_BARRIDO_SEG)


def main() -> None:
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    def shutdown() -> None:
        logger.info("worker_shutdown")
        loop.stop()

    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, shutdown)
        except NotImplementedError:  # pragma: no cover - Windows
            signal.signal(sig, lambda *_: loop.stop())

    try:
        loop.run_until_complete(process_jobs())
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()


if __name__ == "__main__":
    main()
