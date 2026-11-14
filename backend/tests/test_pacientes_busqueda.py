"""Tests de la búsqueda interna de pacientes para el alta de la agenda (C-07).

El alta interna exige `paciente_id`, pero no existía un endpoint para que la
recepción elija un paciente existente de su clínica. `GET
/api/internal/pacientes?q=` resuelve solo eso: búsqueda acotada por clínica,
roles `recepcion|admin`, sin exponer pacientes de otra clínica.
"""

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.db.session import get_session
from app.main import create_app
from tests.turnos_factories import crear_clinica, crear_paciente


def _token(clinic_id: UUID, rol: str) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(uuid4()),
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


async def test_busca_por_nombre_sin_distinguir_mayusculas(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    clinic = await crear_clinica(db_session)
    paciente = await crear_paciente(
        db_session, clinic, nombre="Juana Pérez", telefono="+5491140000001", dni="30111222"
    )
    await crear_paciente(db_session, clinic, nombre="Beto Sosa")

    response = await client.get(
        "/api/internal/pacientes",
        params={"q": "juana"},
        headers=_headers(_token(clinic.id, "recepcion")),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == str(paciente.id)
    assert body[0]["nombre"] == "Juana Pérez"
    assert body[0]["telefono"] == "+5491140000001"
    assert body[0]["dni"] == "30111222"


async def test_busca_por_telefono_y_por_dni(client: AsyncClient, db_session: AsyncSession) -> None:
    clinic = await crear_clinica(db_session)
    paciente = await crear_paciente(
        db_session, clinic, nombre="Carla Díaz", telefono="+5491140000002", dni="28999888"
    )
    headers = _headers(_token(clinic.id, "admin"))

    por_telefono = await client.get(
        "/api/internal/pacientes", params={"q": "40000002"}, headers=headers
    )
    por_dni = await client.get("/api/internal/pacientes", params={"q": "2899"}, headers=headers)

    assert [item["id"] for item in por_telefono.json()] == [str(paciente.id)]
    assert [item["id"] for item in por_dni.json()] == [str(paciente.id)]


async def test_no_expone_pacientes_de_otra_clinica(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    propia = await crear_clinica(db_session)
    ajena = await crear_clinica(db_session)
    await crear_paciente(db_session, ajena, nombre="Paciente Ajeno")
    esperado = await crear_paciente(db_session, propia, nombre="Paciente Propio")

    response = await client.get(
        "/api/internal/pacientes",
        params={"q": "paciente"},
        headers=_headers(_token(propia.id, "recepcion")),
    )

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [str(esperado.id)]


async def test_odontologo_no_puede_buscar_pacientes(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    clinic = await crear_clinica(db_session)

    response = await client.get(
        "/api/internal/pacientes",
        params={"q": "ana"},
        headers=_headers(_token(clinic.id, "odonto")),
    )

    assert response.status_code == 403


@pytest.mark.parametrize("q", ["", "a"])
async def test_q_corto_es_invalido(client: AsyncClient, db_session: AsyncSession, q: str) -> None:
    clinic = await crear_clinica(db_session)

    response = await client.get(
        "/api/internal/pacientes",
        params={"q": q},
        headers=_headers(_token(clinic.id, "recepcion")),
    )

    assert response.status_code == 422


async def test_limita_a_veinte_resultados_ordenados_por_nombre(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    clinic = await crear_clinica(db_session)
    for indice in range(25):
        await crear_paciente(db_session, clinic, nombre=f"Paciente {indice:02d}")

    response = await client.get(
        "/api/internal/pacientes",
        params={"q": "paciente"},
        headers=_headers(_token(clinic.id, "recepcion")),
    )

    body = response.json()
    assert len(body) == 20
    nombres = [item["nombre"] for item in body]
    assert nombres == sorted(nombres)
