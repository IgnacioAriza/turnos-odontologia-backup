"""Tests de API pública del motor de turnos (C-05)."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.personas.models import Paciente
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


async def _clinica_operativa(db_session: AsyncSession) -> dict[str, object]:
    clinic = await crear_clinica(db_session)
    practica = await crear_practica(db_session, clinic, duracion_min=30, precio=Decimal("10000.00"))
    sillon = await crear_sillon(db_session, clinic)
    odonto = await crear_odontologo(db_session, clinic)
    await crear_horario(db_session, clinic, dia_semana=0, desde=time(8, 0), hasta=time(10, 0))
    return {"clinic": clinic, "practica": practica, "sillon": sillon, "odonto": odonto}


@pytest.mark.asyncio
async def test_slots_200_sin_datos_de_pacientes(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _clinica_operativa(db_session)

    response = await client.get(
        "/api/public/slots",
        params={"fecha": LUNES.isoformat(), "practica": str(base["practica"].id)},  # type: ignore[attr-defined]
    )

    assert response.status_code == 200
    body = response.json()
    assert body["fecha"] == LUNES.isoformat()
    assert body["duracion_min"] == 30
    assert len(body["slots"]) == 4
    for slot in body["slots"]:
        assert set(slot) == {"inicio", "fin", "sillon_id", "odontologo_id"}
        texto = str(slot).lower()
        assert "telefono" not in texto
        assert "nombre" not in texto
        assert "dni" not in texto


@pytest.mark.asyncio
async def test_slots_practica_inactiva_404(client: AsyncClient, db_session: AsyncSession) -> None:
    clinic = await crear_clinica(db_session)
    practica = await crear_practica(db_session, clinic, activa=False)

    response = await client.get(
        "/api/public/slots",
        params={"fecha": LUNES.isoformat(), "practica": str(practica.id)},
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_slots_aislados_por_clinica(client: AsyncClient, db_session: AsyncSession) -> None:
    await _clinica_operativa(db_session)
    otra = await crear_clinica(db_session)
    practica_otra = await crear_practica(db_session, otra)

    response = await client.get(
        "/api/public/slots",
        params={"fecha": LUNES.isoformat(), "practica": str(practica_otra.id)},
    )

    assert response.status_code == 200
    assert response.json()["slots"] == []


@pytest.mark.asyncio
async def test_reserva_publica_201(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _clinica_operativa(db_session)

    response = await client.post(
        "/api/public/reservas",
        json={
            "nombre": "Ana",
            "telefono": "+5491112345678",
            "dni": "30111222",
            "practica_id": str(base["practica"].id),  # type: ignore[attr-defined]
            "inicio": local(LUNES, time(8, 0)).isoformat(),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["estado"] == "pendiente_sena"
    assert body["manage_token"]
    assert body["monto_sena"] == "2000.00"

    result = await db_session.execute(select(Paciente).where(Paciente.telefono == "+5491112345678"))
    assert result.scalar_one().nombre == "Ana"


@pytest.mark.asyncio
async def test_reserva_publica_practica_inactiva_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    clinic = await crear_clinica(db_session)
    practica = await crear_practica(db_session, clinic, activa=False)

    response = await client.post(
        "/api/public/reservas",
        json={
            "nombre": "Ana",
            "telefono": "+5491112345678",
            "practica_id": str(practica.id),
            "inicio": local(LUNES, time(8, 0)).isoformat(),
        },
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_reserva_publica_slot_ocupado_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _clinica_operativa(db_session)
    clinic = base["clinic"]
    paciente = await crear_paciente(db_session, clinic)
    await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente,
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=local(LUNES, time(8, 0)),
    )

    response = await client.post(
        "/api/public/reservas",
        json={
            "nombre": "Ana",
            "telefono": "+5491112345678",
            "practica_id": str(base["practica"].id),  # type: ignore[attr-defined]
            "inicio": local(LUNES, time(8, 0)).isoformat(),
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_reserva_publica_paciente_bloqueado_403(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _clinica_operativa(db_session)
    clinic = base["clinic"]
    await crear_paciente(
        db_session,
        clinic,
        telefono="+5491112345678",
        bloqueado_hasta=datetime.now(UTC) + timedelta(days=15),
    )

    response = await client.post(
        "/api/public/reservas",
        json={
            "nombre": "Ana",
            "telefono": "+5491112345678",
            "practica_id": str(base["practica"].id),  # type: ignore[attr-defined]
            "inicio": local(LUNES, time(8, 0)).isoformat(),
        },
    )

    assert response.status_code == 403
    assert "bloqueado hasta" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_inicio_no_alineado_409(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _clinica_operativa(db_session)

    response = await client.post(
        "/api/public/reservas",
        json={
            "nombre": "Ana",
            "telefono": "+5491112345678",
            "practica_id": str(base["practica"].id),  # type: ignore[attr-defined]
            "inicio": local(LUNES, time(8, 7)).isoformat(),
        },
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_slot_liberado_por_expiracion_aparece_en_slots(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _clinica_operativa(db_session)
    clinic = base["clinic"]
    paciente = await crear_paciente(db_session, clinic)
    await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente,
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=local(LUNES, time(8, 0)),
        estado="pendiente_sena",
        expira_at=datetime.now(UTC) - timedelta(minutes=1),
    )

    response = await client.get(
        "/api/public/slots",
        params={"fecha": LUNES.isoformat(), "practica": str(base["practica"].id)},  # type: ignore[attr-defined]
    )

    assert response.status_code == 200
    inicio_local = [
        datetime.fromisoformat(slot["inicio"]).astimezone(local(LUNES, time(0, 0)).tzinfo)
        for slot in response.json()["slots"]
    ]
    assert time(8, 0) in [dt.time() for dt in inicio_local]


@pytest.mark.asyncio
async def test_publico_nunca_devuelve_401(client: AsyncClient, db_session: AsyncSession) -> None:
    """El canal público responde 404/409/403, nunca 401 (interceptor de login)."""
    respuesta_slots = await client.get(
        "/api/public/slots", params={"fecha": "2026-01-05", "practica": str(uuid4())}
    )
    respuesta_reserva = await client.post(
        "/api/public/reservas",
        json={
            "nombre": "Ana",
            "telefono": "+5491112345678",
            "practica_id": str(uuid4()),
            "inicio": "2026-01-05T08:00:00-03:00",
        },
    )

    assert respuesta_slots.status_code != 401
    assert respuesta_reserva.status_code != 401
