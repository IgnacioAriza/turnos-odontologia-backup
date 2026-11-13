"""Contrato del 403 de bloqueo por ausentismo (C-07, tareas 1.3 / 3.2).

El frontend decide qué diálogo mostrar por `codigo`, nunca por el texto. Este
archivo fija el contrato observable en los dos canales de alta:

- público (C-06): 403 `codigo=bloqueado` + `bloqueado_hasta` ISO-8601.
- interno (C-07): mismo cuerpo cuando no hay `motivo_excepcion`.
"""

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
    crear_horario,
    crear_odontologo,
    crear_paciente,
    crear_practica,
    crear_sillon,
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
    await crear_horario(db_session, clinic, dia_semana=0, desde=time(8, 0), hasta=time(20, 0))
    paciente = await crear_paciente(db_session, clinic, telefono="+5491112345678")
    return {
        "clinic": clinic,
        "practica": practica,
        "sillon": sillon,
        "odonto": odonto,
        "paciente": paciente,
    }


@pytest.mark.asyncio
async def test_reserva_publica_bloqueada_expone_codigo_y_fecha(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """El canal público de C-06 gana `codigo` y `bloqueado_hasta` sin perder `detail`."""
    base = await _escenario(db_session)
    hasta = datetime.now(UTC) + timedelta(days=15)
    base["paciente"].bloqueado_hasta = hasta  # type: ignore[attr-defined]
    await db_session.flush()

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
    assert response.headers["content-type"].startswith("application/problem+json")
    body = response.json()
    assert body["codigo"] == "bloqueado"
    assert datetime.fromisoformat(body["bloqueado_hasta"]) == hasta
    assert "bloqueado" in body["detail"].lower()


@pytest.mark.asyncio
async def test_alta_interna_bloqueada_expone_codigo_y_fecha(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Sin `motivo_excepcion` el alta interna responde el mismo contrato 403."""
    base = await _escenario(db_session)
    hasta = datetime.now(UTC) + timedelta(days=15)
    base["paciente"].bloqueado_hasta = hasta  # type: ignore[attr-defined]
    await db_session.flush()
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    response = await client.post(
        "/api/internal/turnos",
        json={
            "paciente_id": str(base["paciente"].id),  # type: ignore[attr-defined]
            "sillon_id": str(base["sillon"].id),  # type: ignore[attr-defined]
            "odontologo_id": str(base["odonto"].id),  # type: ignore[attr-defined]
            "tipo_practica_id": str(base["practica"].id),  # type: ignore[attr-defined]
            "inicio": local(LUNES, time(8, 0)).isoformat(),
        },
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403
    body = response.json()
    assert body["codigo"] == "bloqueado"
    assert datetime.fromisoformat(body["bloqueado_hasta"]) == hasta
