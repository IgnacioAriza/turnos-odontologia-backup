"""Tests del catálogo público de prácticas (C-06, ampliación 8b)."""

from collections.abc import AsyncGenerator
from datetime import time
from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.session import get_session
from app.main import create_app
from tests.turnos_factories import (
    LUNES,
    crear_clinica,
    crear_horario,
    crear_odontologo,
    crear_paciente,
    crear_practica,
    crear_sillon,
    crear_turno,
    local,
)


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


@pytest.mark.asyncio
async def test_catalogo_publico_devuelve_solo_activas_ordenadas(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    clinic = await crear_clinica(db_session)
    await crear_practica(db_session, clinic, nombre="Zeta", duracion_min=60, sena_pct=30)
    await crear_practica(db_session, clinic, nombre="Alfa", duracion_min=30, sena_pct=20)
    await crear_practica(db_session, clinic, nombre="Beta", activa=False)

    response = await client.get("/api/public/practicas")

    assert response.status_code == 200
    body = response.json()
    assert [p["nombre"] for p in body] == ["Alfa", "Zeta"]
    assert set(body[0]) == {"id", "nombre", "duracion_min", "sena_pct"}
    assert body[0]["duracion_min"] == 30
    assert body[0]["sena_pct"] == 20


@pytest.mark.asyncio
async def test_catalogo_no_expone_datos_internos(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    clinic = await crear_clinica(db_session)
    await crear_practica(db_session, clinic, nombre="Limpieza", precio=Decimal("12345.00"))

    response = await client.get("/api/public/practicas")

    assert response.status_code == 200
    texto = response.text.lower()
    assert "precio_base" not in texto
    assert "12345.00" not in texto
    assert "clinic_id" not in texto


@pytest.mark.asyncio
async def test_catalogo_vacio_devuelve_lista_vacia(client: AsyncClient) -> None:
    response = await client.get("/api/public/practicas")

    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_solape_publico_trae_codigo_estable(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    clinic = await crear_clinica(db_session)
    practica = await crear_practica(db_session, clinic, duracion_min=30)
    sillon = await crear_sillon(db_session, clinic)
    odonto = await crear_odontologo(db_session, clinic)
    await crear_horario(db_session, clinic, dia_semana=0, desde=time(8, 0), hasta=time(10, 0))
    paciente = await crear_paciente(db_session, clinic)
    await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente,
        sillon=sillon,
        odontologo=odonto,
        practica=practica,
        inicio=local(LUNES, time(8, 0)),
    )

    response = await client.post(
        "/api/public/reservas",
        json={
            "nombre": "Ana",
            "telefono": "+5491112345678",
            "practica_id": str(practica.id),
            "inicio": local(LUNES, time(8, 0)).isoformat(),
        },
    )

    assert response.status_code == 409
    assert response.json()["codigo"] == "solape"
