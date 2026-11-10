"""Tests de API interna de turnos con RBAC (C-05)."""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.db.session import get_session
from app.main import create_app
from tests.turnos_factories import (
    LUNES,
    crear_clinica,
    crear_odontologo,
    crear_paciente,
    crear_practica,
    crear_sillon,
    crear_turno,
    local,
)


def _token(clinic_id: UUID, rol: str, sub: UUID | None = None) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(sub or uuid4()),
        "clinic_id": str(clinic_id),
        "rol": rol,
        "email": f"{rol}@clinica.com",
        "jti": str(uuid4()),
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=30),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


async def _escenario(db_session: AsyncSession) -> dict[str, object]:
    clinic = await crear_clinica(db_session)
    practica = await crear_practica(db_session, clinic, precio=Decimal("10000.00"))
    sillon = await crear_sillon(db_session, clinic)
    odonto = await crear_odontologo(db_session, clinic)
    paciente = await crear_paciente(db_session, clinic)
    return {
        "clinic": clinic,
        "practica": practica,
        "sillon": sillon,
        "odonto": odonto,
        "paciente": paciente,
    }


def _payload(base: dict[str, object], hora: time = time(10, 0)) -> dict[str, str]:
    return {
        "paciente_id": str(base["paciente"].id),  # type: ignore[attr-defined]
        "sillon_id": str(base["sillon"].id),  # type: ignore[attr-defined]
        "odontologo_id": str(base["odonto"].id),  # type: ignore[attr-defined]
        "tipo_practica_id": str(base["practica"].id),  # type: ignore[attr-defined]
        "inicio": local(LUNES, hora).isoformat(),
    }


@pytest.mark.asyncio
async def test_recepcion_crea_turno_sin_manage_token(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    response = await client.post(
        "/api/internal/turnos", json=_payload(base), headers=_headers(token)
    )

    assert response.status_code == 201
    body = response.json()
    assert body["manage_token"] is None
    assert body["estado"] == "confirmado"
    assert body["monto_sena"] == "2000.00"


@pytest.mark.asyncio
async def test_admin_crea_turno(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    token = _token(base["clinic"].id, "admin")  # type: ignore[attr-defined]

    response = await client.post(
        "/api/internal/turnos", json=_payload(base), headers=_headers(token)
    )

    assert response.status_code == 201


@pytest.mark.asyncio
async def test_odonto_403(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    token = _token(base["clinic"].id, "odonto")  # type: ignore[attr-defined]

    response = await client.post(
        "/api/internal/turnos", json=_payload(base), headers=_headers(token)
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_sin_token_401(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario(db_session)

    response = await client.post("/api/internal/turnos", json=_payload(base))

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_recurso_de_otra_clinica_404(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    otra = await crear_clinica(db_session)
    sillon_ajeno = await crear_sillon(db_session, otra, "Sillón ajeno")
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    payload = _payload(base)
    payload["sillon_id"] = str(sillon_ajeno.id)

    response = await client.post("/api/internal/turnos", json=payload, headers=_headers(token))

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_solape_sillon_409(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    await crear_turno(
        db_session,
        clinic=base["clinic"],  # type: ignore[arg-type]
        paciente=base["paciente"],  # type: ignore[arg-type]
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=local(LUNES, time(10, 0)),
    )
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    response = await client.post(
        "/api/internal/turnos", json=_payload(base, time(10, 0)), headers=_headers(token)
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_paciente_bloqueado_403(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    base["paciente"].bloqueado_hasta = datetime.now(UTC) + timedelta(days=10)  # type: ignore[attr-defined]
    await db_session.flush()
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    response = await client.post(
        "/api/internal/turnos", json=_payload(base), headers=_headers(token)
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_endpoints_en_openapi(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/public/slots" in paths
    assert "/api/public/reservas" in paths
    assert "/api/internal/turnos" in paths
