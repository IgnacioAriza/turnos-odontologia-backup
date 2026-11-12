"""Tests del puerto de recordatorios y su implementación no-op (C-06, tarea 5.1)."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.notificaciones import NoOpRecordatorio, RecordatorioPort


def test_noop_cumple_el_puerto() -> None:
    assert isinstance(NoOpRecordatorio(), RecordatorioPort)


@pytest.mark.asyncio
async def test_noop_cancelar_no_falla() -> None:
    await NoOpRecordatorio().cancelar(uuid4())


@pytest.mark.asyncio
async def test_noop_reprogramar_no_falla() -> None:
    await NoOpRecordatorio().reprogramar(uuid4(), datetime.now(UTC))


@pytest.mark.asyncio
async def test_noop_registra_la_llamada_en_log(capsys: pytest.CaptureFixture[str]) -> None:
    turno_id = uuid4()

    await NoOpRecordatorio().cancelar(turno_id)

    salida = capsys.readouterr().out
    assert "recordatorio_cancelado" in salida
    assert str(turno_id) in salida
