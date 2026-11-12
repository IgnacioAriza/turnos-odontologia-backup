"""Tests de la API pública de gestión por token (C-06, tareas 6.1–6.5 y 6.7)."""

from collections.abc import AsyncGenerator
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_session
from app.main import create_app
from tests.turnos_factories import (
    crear_clinica,
    crear_horario,
    crear_odontologo,
    crear_paciente,
    crear_practica,
    crear_sillon,
    crear_turno,
)

AR = ZoneInfo("America/Argentina/Buenos_Aires")
TOKEN = "token-de-gestion-1234567890"


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def _override_session() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_session] = _override_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


def _redondear(momento: datetime) -> datetime:
    return momento.replace(minute=(momento.minute // 30) * 30, second=0, microsecond=0)


async def _turno(
    db: AsyncSession,
    *,
    delta_horas: int = 30,
    estado: str = "confirmado",
    monto_sena: Decimal = Decimal("2000.00"),
    manage_token: str | None = TOKEN,
    is_active: bool = True,
    reprogramaciones_count: int = 0,
) -> dict[str, Any]:
    clinic = await crear_clinica(db)
    practica = await crear_practica(db, clinic, duracion_min=30, precio=Decimal("10000.00"))
    sillon = await crear_sillon(db, clinic)
    odonto = await crear_odontologo(db, clinic)
    paciente = await crear_paciente(db, clinic)
    objetivo = _redondear(datetime.now(AR) + timedelta(hours=delta_horas))
    await crear_horario(
        db,
        clinic,
        dia_semana=objetivo.weekday(),
        desde=time(0, 0),
        hasta=time(23, 30),
    )
    turno = await crear_turno(
        db,
        clinic=clinic,
        paciente=paciente,
        sillon=sillon,
        odontologo=odonto,
        practica=practica,
        inicio=objetivo,
        estado=estado,
        monto_sena=monto_sena,
        manage_token=manage_token,
        reprogramaciones_count=reprogramaciones_count,
    )
    turno.is_active = is_active
    await db.commit()
    return {
        "clinic": clinic,
        "practica": practica,
        "sillon": sillon,
        "odonto": odonto,
        "paciente": paciente,
        "turno": turno,
        "objetivo": objetivo,
        "fecha": objetivo.date(),
    }


@pytest.mark.asyncio
async def test_get_gestion_devuelve_el_turno_sin_token(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _turno(db_session)

    response = await client.get(f"/api/public/gestion/{TOKEN}")

    assert response.status_code == 200
    body = response.json()
    assert body["turno_id"] == str(base["turno"].id)
    assert body["estado"] == "confirmado"
    assert body["practica"]["nombre"] == "Limpieza"
    assert body["monto_sena"] == "2000.00"
    assert body["reprogramaciones_count"] == 0
    assert body["reprogramaciones_restantes"] == 1
    assert body["sena_perdida"] is False
    assert body["dentro_de_ventana"] is True
    assert "manage_token" not in body
    assert TOKEN not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


@pytest.mark.asyncio
async def test_token_invalido_es_403_y_nunca_401(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _turno(db_session)

    response = await client.get("/api/public/gestion/token-que-no-existe")

    assert response.status_code == 403
    assert response.status_code != 401
    assert response.json()["codigo"] == "token_invalido"


@pytest.mark.asyncio
async def test_turno_borrado_es_404(client: AsyncClient, db_session: AsyncSession) -> None:
    await _turno(db_session, is_active=False)

    response = await client.get(f"/api/public/gestion/{TOKEN}")

    assert response.status_code == 404
    assert response.json()["codigo"] == "turno_no_encontrado"


@pytest.mark.asyncio
async def test_log_registra_turno_id_y_no_el_token(
    client: AsyncClient, db_session: AsyncSession, capsys: pytest.CaptureFixture[str]
) -> None:
    base = await _turno(db_session)

    await client.get(f"/api/public/gestion/{TOKEN}")

    salida = capsys.readouterr().out
    assert str(base["turno"].id) in salida
    assert TOKEN not in salida


@pytest.mark.asyncio
async def test_log_de_error_tampoco_filtra_el_token(
    client: AsyncClient, capsys: pytest.CaptureFixture[str]
) -> None:
    await client.get("/api/public/gestion/token-invalido-que-no-existe")

    salida = capsys.readouterr().out
    assert "token-invalido-que-no-existe" not in salida


@pytest.mark.asyncio
async def test_cancelar_dentro_de_ventana(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _turno(db_session)

    response = await client.post(
        f"/api/public/gestion/{TOKEN}/cancelar", json={"manage_token": TOKEN}
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "cancelado"
    await db_session.refresh(base["turno"])
    assert base["turno"].sena_perdida is False


@pytest.mark.asyncio
async def test_cancelar_tarde_sin_confirmar_da_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _turno(db_session, delta_horas=5)

    response = await client.post(
        f"/api/public/gestion/{TOKEN}/cancelar", json={"manage_token": TOKEN}
    )

    assert response.status_code == 409
    body = response.json()
    assert body["codigo"] == "requiere_confirmacion"
    assert body["perdida_sena"] is True
    await db_session.refresh(base["turno"])
    assert base["turno"].estado == "confirmado"


@pytest.mark.asyncio
async def test_cancelar_tarde_confirmando(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _turno(db_session, delta_horas=5)

    response = await client.post(
        f"/api/public/gestion/{TOKEN}/cancelar",
        json={"manage_token": TOKEN, "confirmar_perdida_sena": True},
    )

    assert response.status_code == 200
    await db_session.refresh(base["turno"])
    assert base["turno"].estado == "cancelado"
    assert base["turno"].sena_perdida is True


@pytest.mark.asyncio
async def test_cancelar_con_token_del_cuerpo_distinto_da_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _turno(db_session)

    response = await client.post(
        f"/api/public/gestion/{TOKEN}/cancelar", json={"manage_token": "otro-token"}
    )

    assert response.status_code == 403
    assert response.json()["codigo"] == "token_invalido"


@pytest.mark.asyncio
async def test_cancelar_sin_token_en_el_cuerpo_da_422(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _turno(db_session)

    response = await client.post(f"/api/public/gestion/{TOKEN}/cancelar", json={})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_reprogramar_primera_vez(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _turno(db_session)
    nuevo_inicio = base["objetivo"] + timedelta(hours=1)

    response = await client.post(
        f"/api/public/gestion/{TOKEN}/reprogramar",
        json={"manage_token": TOKEN, "nuevo_inicio": nuevo_inicio.isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["turno_id"] == str(base["turno"].id)
    assert body["reprogramaciones_count"] == 1
    assert body["reprogramaciones_restantes"] == 0


@pytest.mark.asyncio
async def test_segunda_reprogramacion_sin_confirmar_da_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _turno(db_session, reprogramaciones_count=1)
    nuevo_inicio = base["objetivo"] + timedelta(hours=1)

    response = await client.post(
        f"/api/public/gestion/{TOKEN}/reprogramar",
        json={"manage_token": TOKEN, "nuevo_inicio": nuevo_inicio.isoformat()},
    )

    assert response.status_code == 409
    assert response.json()["codigo"] == "requiere_nueva_sena"


@pytest.mark.asyncio
async def test_exceso_de_intentos_por_token_da_429(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    await _turno(db_session)

    for _ in range(10):
        response = await client.get(f"/api/public/gestion/{TOKEN}")
        assert response.status_code == 200

    response = await client.get(f"/api/public/gestion/{TOKEN}")

    assert response.status_code == 429
    assert response.json()["codigo"] == "rate_limited"
    assert int(response.headers["Retry-After"]) >= 0


@pytest.mark.asyncio
async def test_fecha_de_hoy_no_rompe_la_vista(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """El GET no expone la fecha del servidor ni depende de horarios de atención."""
    base = await _turno(db_session)
    assert base["fecha"] > date.today()
