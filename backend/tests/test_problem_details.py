"""Tests del envelope problem+json con `codigo` y datos extra (C-06, design D4)."""

from collections.abc import AsyncGenerator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.exceptions import (
    ConflictError,
    ForbiddenError,
    NotFoundError,
    RateLimitError,
    UnprocessableError,
    register_exception_handlers,
)


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/conflicto")
    async def conflicto() -> None:
        raise ConflictError("Horario ocupado", code="solape")

    @app.get("/confirmacion")
    async def confirmacion() -> None:
        raise ConflictError(
            "Cancelar pierde la seña",
            code="requiere_confirmacion",
            extra={"perdida_sena": True},
        )

    @app.get("/prohibido")
    async def prohibido() -> None:
        raise ForbiddenError("Token inválido", code="token_invalido")

    @app.get("/no-encontrado")
    async def no_encontrado() -> None:
        raise NotFoundError("Turno no encontrado", code="turno_no_encontrado")

    @app.get("/invalido")
    async def invalido() -> None:
        raise UnprocessableError("Slot inválido", code="slot_invalido")

    @app.get("/limitado")
    async def limitado() -> None:
        raise RateLimitError(retry_after=30)

    @app.get("/sin-codigo")
    async def sin_codigo() -> None:
        raise ConflictError("Conflicto clásico")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_conflicto_lleva_codigo(client: AsyncClient) -> None:
    response = await client.get("/conflicto")

    assert response.status_code == 409
    assert response.json()["codigo"] == "solape"
    assert response.headers["content-type"] == "application/problem+json"


@pytest.mark.asyncio
async def test_extra_se_funde_en_el_cuerpo(client: AsyncClient) -> None:
    response = await client.get("/confirmacion")

    assert response.status_code == 409
    body = response.json()
    assert body["codigo"] == "requiere_confirmacion"
    assert body["perdida_sena"] is True


@pytest.mark.asyncio
async def test_prohibido_nunca_es_401(client: AsyncClient) -> None:
    response = await client.get("/prohibido")

    assert response.status_code == 403
    assert response.json()["codigo"] == "token_invalido"


@pytest.mark.asyncio
async def test_no_encontrado(client: AsyncClient) -> None:
    response = await client.get("/no-encontrado")

    assert response.status_code == 404
    assert response.json()["codigo"] == "turno_no_encontrado"


@pytest.mark.asyncio
async def test_unprocessable(client: AsyncClient) -> None:
    response = await client.get("/invalido")

    assert response.status_code == 422
    assert response.json()["codigo"] == "slot_invalido"


@pytest.mark.asyncio
async def test_rate_limit_trae_retry_after_y_codigo(client: AsyncClient) -> None:
    response = await client.get("/limitado")

    assert response.status_code == 429
    assert response.headers["Retry-After"] == "30"
    assert response.json()["codigo"] == "rate_limited"


@pytest.mark.asyncio
async def test_error_sin_codigo_no_agrega_llaves(client: AsyncClient) -> None:
    response = await client.get("/sin-codigo")

    body = response.json()
    assert "codigo" not in body
    assert set(body) == {"type", "title", "status", "detail", "instance"}
