"""Tests de API del catálogo: lecturas internas, admin y cambio de % seña."""

from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.clinica.models import Arancel, AuditoriaSena, Clinic, Sillon, TipoPractica
from app.domain.personas import models as _personas_models  # noqa: F401
from app.domain.personas.models import User
from app.infrastructure.db.session import get_session
from app.main import create_app


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


async def _setup_clinic(
    db_session: AsyncSession, nombre: str
) -> tuple[Clinic, list[TipoPractica], list[Sillon]]:
    clinic = Clinic(nombre=nombre, timezone="America/Argentina/Buenos_Aires")
    db_session.add(clinic)
    await db_session.flush()

    practicas = [
        TipoPractica(
            clinic_id=clinic.id,
            nombre="Limpieza",
            duracion_min=30,
            precio_base=Decimal("15000.00"),
            sena_pct=30,
            activa=True,
        ),
        TipoPractica(
            clinic_id=clinic.id,
            nombre="Endodoncia",
            duracion_min=60,
            precio_base=Decimal("45000.00"),
            sena_pct=30,
            activa=True,
        ),
        TipoPractica(
            clinic_id=clinic.id,
            nombre="Práctica inactiva",
            duracion_min=20,
            precio_base=Decimal("1000.00"),
            sena_pct=10,
            activa=False,
        ),
    ]
    sillones = [
        Sillon(clinic_id=clinic.id, nombre="Sillón 1", activo=True),
        Sillon(clinic_id=clinic.id, nombre="Sillón 2", activo=False),
    ]
    db_session.add_all(practicas)
    db_session.add_all(sillones)
    await db_session.flush()
    return clinic, practicas, sillones


# --- GET /api/internal/tipos-practica -------------------------------------


@pytest.mark.asyncio
async def test_tipos_practica_recepcion_200(client: AsyncClient, db_session: AsyncSession):
    clinic, _, _ = await _setup_clinic(db_session, "Clínica Tipos Recepción")

    response = await client.get(
        "/api/internal/tipos-practica", headers=_headers(_token(clinic.id, "recepcion"))
    )

    assert response.status_code == 200
    data = response.json()
    nombres = {item["nombre"] for item in data}
    assert nombres == {"Limpieza", "Endodoncia"}


@pytest.mark.asyncio
async def test_tipos_practica_odonto_200(client: AsyncClient, db_session: AsyncSession):
    clinic, _, _ = await _setup_clinic(db_session, "Clínica Tipos Odonto")

    response = await client.get(
        "/api/internal/tipos-practica", headers=_headers(_token(clinic.id, "odonto"))
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tipos_practica_admin_200(client: AsyncClient, db_session: AsyncSession):
    clinic, _, _ = await _setup_clinic(db_session, "Clínica Tipos Admin")

    response = await client.get(
        "/api/internal/tipos-practica", headers=_headers(_token(clinic.id, "admin"))
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_tipos_practica_sin_token_401(client: AsyncClient):
    response = await client.get("/api/internal/tipos-practica")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_tipos_practica_no_devuelve_otra_clinica(
    client: AsyncClient, db_session: AsyncSession
):
    clinic_a, _, _ = await _setup_clinic(db_session, "Clínica A Tipos")
    await _setup_clinic(db_session, "Clínica B Tipos")

    response = await client.get(
        "/api/internal/tipos-practica", headers=_headers(_token(clinic_a.id, "recepcion"))
    )

    assert response.status_code == 200
    nombres = {item["nombre"] for item in response.json()}
    assert nombres == {"Limpieza", "Endodoncia"}


# --- GET /api/internal/sillones -------------------------------------------


@pytest.mark.asyncio
async def test_sillones_solo_activos(client: AsyncClient, db_session: AsyncSession):
    clinic, _, _ = await _setup_clinic(db_session, "Clínica Sillones")

    response = await client.get(
        "/api/internal/sillones", headers=_headers(_token(clinic.id, "recepcion"))
    )

    assert response.status_code == 200
    nombres = {item["nombre"] for item in response.json()}
    assert nombres == {"Sillón 1"}


@pytest.mark.asyncio
async def test_sillones_sin_token_401(client: AsyncClient):
    response = await client.get("/api/internal/sillones")

    assert response.status_code == 401


# --- GET /api/admin/aranceles ---------------------------------------------


@pytest.mark.asyncio
async def test_admin_aranceles_200(client: AsyncClient, db_session: AsyncSession):
    clinic, practicas, _ = await _setup_clinic(db_session, "Clínica Admin Aranceles")
    db_session.add(
        Arancel(
            tipo_practica_id=practicas[0].id,
            precio=Decimal("18000.00"),
            sena_pct=30,
            vigente_desde=date(2026, 1, 1),
        )
    )
    await db_session.flush()

    response = await client.get(
        "/api/admin/aranceles", headers=_headers(_token(clinic.id, "admin"))
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 3
    limpieza = next(item for item in data if item["nombre"] == "Limpieza")
    assert limpieza["precio"] == 18000.0
    assert limpieza["sena_pct"] == 30
    assert limpieza["duracion_min"] == 30


@pytest.mark.asyncio
async def test_admin_aranceles_recepcion_403(client: AsyncClient, db_session: AsyncSession):
    clinic, _, _ = await _setup_clinic(db_session, "Clínica Aranceles Recepción")

    response = await client.get(
        "/api/admin/aranceles", headers=_headers(_token(clinic.id, "recepcion"))
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_aranceles_odonto_403(client: AsyncClient, db_session: AsyncSession):
    clinic, _, _ = await _setup_clinic(db_session, "Clínica Aranceles Odonto")

    response = await client.get(
        "/api/admin/aranceles", headers=_headers(_token(clinic.id, "odonto"))
    )

    assert response.status_code == 403


# --- PATCH /api/admin/tipos-practica/{id}/sena-pct ------------------------


async def _setup_admin_user(db_session: AsyncSession, clinic: Clinic) -> User:
    admin = User(
        clinic_id=clinic.id,
        email="admin-c04@clinica.com",
        password_hash="hash",
        rol="admin",
        activo=True,
    )
    db_session.add(admin)
    await db_session.flush()
    return admin


@pytest.mark.asyncio
async def test_patch_sena_200_y_audita(client: AsyncClient, db_session: AsyncSession):
    clinic, practicas, _ = await _setup_clinic(db_session, "Clínica PATCH Seña")
    admin = await _setup_admin_user(db_session, clinic)
    practica = practicas[0]

    response = await client.patch(
        f"/api/admin/tipos-practica/{practica.id}/sena-pct",
        json={"sena_pct": 40},
        headers=_headers(_token(clinic.id, "admin", sub=admin.id)),
    )

    assert response.status_code == 200
    assert response.json()["sena_pct"] == 40

    result = await db_session.execute(
        select(AuditoriaSena).where(AuditoriaSena.tipo_practica_id == practica.id)
    )
    auditoria = result.scalar_one()
    assert auditoria.valor_anterior == 30
    assert auditoria.valor_nuevo == 40
    assert auditoria.usuario_id == admin.id


@pytest.mark.asyncio
async def test_patch_sena_422_fuera_de_rango(client: AsyncClient, db_session: AsyncSession):
    clinic, practicas, _ = await _setup_clinic(db_session, "Clínica PATCH Inválido")
    admin = await _setup_admin_user(db_session, clinic)

    response = await client.patch(
        f"/api/admin/tipos-practica/{practicas[0].id}/sena-pct",
        json={"sena_pct": 150},
        headers=_headers(_token(clinic.id, "admin", sub=admin.id)),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_sena_403_no_admin(client: AsyncClient, db_session: AsyncSession):
    clinic, practicas, _ = await _setup_clinic(db_session, "Clínica PATCH RBAC")

    response = await client.patch(
        f"/api/admin/tipos-practica/{practicas[0].id}/sena-pct",
        json={"sena_pct": 40},
        headers=_headers(_token(clinic.id, "recepcion")),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_patch_sena_404_otra_clinica(client: AsyncClient, db_session: AsyncSession):
    clinic_a, _, _ = await _setup_clinic(db_session, "Clínica PATCH A")
    _, practicas_b, _ = await _setup_clinic(db_session, "Clínica PATCH B")
    admin = await _setup_admin_user(db_session, clinic_a)

    response = await client.patch(
        f"/api/admin/tipos-practica/{practicas_b[0].id}/sena-pct",
        json={"sena_pct": 40},
        headers=_headers(_token(clinic_a.id, "admin", sub=admin.id)),
    )

    assert response.status_code == 404
