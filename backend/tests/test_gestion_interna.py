"""Tests de la API interna de gestión de turnos (C-06, tareas 7.1 y 7.3)."""

import json
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.clinica.models import Clinic
from app.domain.turnos.models import Turno
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
MOTIVO = "Paciente reprogramó por teléfono"


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


def _en_dias(dias: int, hora: time) -> datetime:
    return datetime.combine(datetime.now(AR).date() + timedelta(days=dias), hora, tzinfo=AR)


async def _escenario(
    db: AsyncSession,
    *,
    inicio: datetime | None = None,
    estado: str = "confirmado",
    monto_sena: Decimal = Decimal("2000.00"),
    reprogramaciones_count: int = 0,
    clinic: Clinic | None = None,
) -> dict[str, Any]:
    clinic = clinic or await crear_clinica(db)
    practica = await crear_practica(db, clinic, duracion_min=30, precio=Decimal("10000.00"))
    sillon = await crear_sillon(db, clinic)
    odonto = await crear_odontologo(db, clinic)
    paciente = await crear_paciente(db, clinic)
    inicio = inicio or _en_dias(2, time(10, 0))
    await crear_horario(
        db,
        clinic,
        dia_semana=inicio.weekday(),
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
        inicio=inicio,
        estado=estado,
        monto_sena=monto_sena,
        manage_token=f"token-{uuid4().hex}",
        reprogramaciones_count=reprogramaciones_count,
    )
    await db.commit()
    return {
        "clinic": clinic,
        "practica": practica,
        "sillon": sillon,
        "odonto": odonto,
        "paciente": paciente,
        "turno": turno,
        "inicio": inicio,
    }


async def _contar_turnos(db: AsyncSession) -> int:
    result = await db.execute(select(func.count()).select_from(Turno))
    return int(result.scalar_one())


def _iso_utc(momento: datetime) -> str:
    return momento.astimezone(UTC).isoformat()


def _cancelar_url(base: dict[str, Any]) -> str:
    return f"/api/internal/turnos/{base['turno'].id}/cancelar"


def _reprogramar_url(base: dict[str, Any]) -> str:
    return f"/api/internal/turnos/{base['turno'].id}/reprogramar"


# --- RBAC y validación de entrada -------------------------------------------


@pytest.mark.asyncio
async def test_recepcion_cancela_con_motivo_y_lo_audita(
    client: AsyncClient, db_session: AsyncSession, capsys: pytest.CaptureFixture[str]
) -> None:
    base = await _escenario(db_session)
    usuario_id = uuid4()
    token = _token(base["clinic"].id, "recepcion", sub=usuario_id)

    response = await client.post(
        _cancelar_url(base), json={"motivo": MOTIVO}, headers=_headers(token)
    )

    assert response.status_code == 200
    body = response.json()
    assert body["estado"] == "cancelado"
    assert body["id"] == str(base["turno"].id)
    assert "manage_token" not in body
    await db_session.refresh(base["turno"])
    assert base["turno"].estado == "cancelado"

    salida = capsys.readouterr().out
    assert "turno_cancelado" in salida
    assert str(base["turno"].id) in salida
    assert str(usuario_id) in salida
    # El logger serializa JSON con escapes ASCII; comparar la forma escapada.
    assert json.dumps(MOTIVO)[1:-1] in salida
    assert base["turno"].manage_token not in salida


@pytest.mark.asyncio
async def test_admin_cancela(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    token = _token(base["clinic"].id, "admin")

    response = await client.post(
        _cancelar_url(base), json={"motivo": MOTIVO}, headers=_headers(token)
    )

    assert response.status_code == 200
    assert response.json()["estado"] == "cancelado"


@pytest.mark.asyncio
@pytest.mark.parametrize("accion", ["cancelar", "reprogramar"])
async def test_odonto_recibe_403(
    client: AsyncClient, db_session: AsyncSession, accion: str
) -> None:
    base = await _escenario(db_session)
    token = _token(base["clinic"].id, "odonto")
    url = _cancelar_url(base) if accion == "cancelar" else _reprogramar_url(base)
    payload = (
        {"motivo": MOTIVO}
        if accion == "cancelar"
        else {"motivo": MOTIVO, "nuevo_inicio": _iso_utc(base["inicio"] + timedelta(hours=1))}
    )

    response = await client.post(url, json=payload, headers=_headers(token))

    assert response.status_code == 403
    await db_session.refresh(base["turno"])
    assert base["turno"].estado == "confirmado"


@pytest.mark.asyncio
@pytest.mark.parametrize("accion", ["cancelar", "reprogramar"])
async def test_turno_de_otra_clinica_da_404(
    client: AsyncClient, db_session: AsyncSession, accion: str
) -> None:
    base = await _escenario(db_session)
    otra = await crear_clinica(db_session)
    token = _token(otra.id, "recepcion")
    url = _cancelar_url(base) if accion == "cancelar" else _reprogramar_url(base)
    payload = (
        {"motivo": MOTIVO}
        if accion == "cancelar"
        else {"motivo": MOTIVO, "nuevo_inicio": _iso_utc(base["inicio"] + timedelta(hours=1))}
    )

    response = await client.post(url, json=payload, headers=_headers(token))

    assert response.status_code == 404
    assert response.json()["codigo"] == "turno_no_encontrado"
    await db_session.refresh(base["turno"])
    assert base["turno"].estado == "confirmado"
    assert base["turno"].reprogramaciones_count == 0


@pytest.mark.asyncio
async def test_cancelar_sin_motivo_da_422_y_no_cambia_nada(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario(db_session)
    token = _token(base["clinic"].id, "recepcion")

    response = await client.post(_cancelar_url(base), json={}, headers=_headers(token))

    assert response.status_code == 422
    await db_session.refresh(base["turno"])
    assert base["turno"].estado == "confirmado"


@pytest.mark.asyncio
async def test_motivo_en_blanco_da_422(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    token = _token(base["clinic"].id, "recepcion")

    response = await client.post(
        _cancelar_url(base), json={"motivo": "   "}, headers=_headers(token)
    )

    assert response.status_code == 422
    await db_session.refresh(base["turno"])
    assert base["turno"].estado == "confirmado"


@pytest.mark.asyncio
async def test_reprogramar_sin_motivo_da_422(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    token = _token(base["clinic"].id, "recepcion")

    response = await client.post(
        _reprogramar_url(base),
        json={"nuevo_inicio": _iso_utc(base["inicio"] + timedelta(hours=1))},
        headers=_headers(token),
    )

    assert response.status_code == 422
    await db_session.refresh(base["turno"])
    assert base["turno"].reprogramaciones_count == 0


@pytest.mark.asyncio
async def test_sin_token_da_401(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario(db_session)

    response = await client.post(_cancelar_url(base), json={"motivo": MOTIVO})

    assert response.status_code == 401


# --- Mismas reglas de dominio que el canal público ---------------------------


@pytest.mark.asyncio
async def test_cancelar_tarde_sin_confirmar_da_409_requiere_confirmacion(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario(db_session, inicio=datetime.now(AR) + timedelta(hours=5))
    token = _token(base["clinic"].id, "recepcion")

    response = await client.post(
        _cancelar_url(base), json={"motivo": MOTIVO}, headers=_headers(token)
    )

    assert response.status_code == 409
    body = response.json()
    assert body["codigo"] == "requiere_confirmacion"
    assert body["perdida_sena"] is True
    await db_session.refresh(base["turno"])
    assert base["turno"].estado == "confirmado"


@pytest.mark.asyncio
async def test_cancelar_tarde_confirmando_marca_sena_perdida(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario(db_session, inicio=datetime.now(AR) + timedelta(hours=5))
    token = _token(base["clinic"].id, "recepcion")

    response = await client.post(
        _cancelar_url(base),
        json={"motivo": MOTIVO, "confirmar_perdida_sena": True},
        headers=_headers(token),
    )

    assert response.status_code == 200
    assert response.json()["sena_perdida"] is True
    await db_session.refresh(base["turno"])
    assert base["turno"].estado == "cancelado"
    assert base["turno"].sena_perdida is True


@pytest.mark.asyncio
async def test_reprogramar_primera_vez_reusa_el_motor_de_slots(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario(db_session)
    token = _token(base["clinic"].id, "recepcion")
    nuevo_inicio = base["inicio"] + timedelta(hours=1)

    response = await client.post(
        _reprogramar_url(base),
        json={"motivo": MOTIVO, "nuevo_inicio": _iso_utc(nuevo_inicio)},
        headers=_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(base["turno"].id)
    assert body["reprogramaciones_count"] == 1
    assert datetime.fromisoformat(body["inicio"]) == nuevo_inicio.astimezone(UTC)
    await db_session.refresh(base["turno"])
    assert base["turno"].reprogramaciones_count == 1


@pytest.mark.asyncio
async def test_reprogramar_a_horario_ocupado_da_409_solape(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario(db_session)
    otro_paciente = await crear_paciente(db_session, base["clinic"])
    await crear_turno(
        db_session,
        clinic=base["clinic"],
        paciente=otro_paciente,
        sillon=base["sillon"],
        odontologo=base["odonto"],
        practica=base["practica"],
        inicio=base["inicio"] + timedelta(hours=1),
    )
    await db_session.commit()
    token = _token(base["clinic"].id, "recepcion")

    response = await client.post(
        _reprogramar_url(base),
        json={
            "motivo": MOTIVO,
            "nuevo_inicio": _iso_utc(base["inicio"] + timedelta(hours=1)),
        },
        headers=_headers(token),
    )

    assert response.status_code == 409
    assert response.json()["codigo"] == "solape"
    await db_session.refresh(base["turno"])
    assert base["turno"].reprogramaciones_count == 0


@pytest.mark.asyncio
async def test_segunda_reprogramacion_sin_confirmar_da_409_requiere_nueva_sena(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario(db_session, reprogramaciones_count=1)
    token = _token(base["clinic"].id, "recepcion")

    response = await client.post(
        _reprogramar_url(base),
        json={
            "motivo": MOTIVO,
            "nuevo_inicio": _iso_utc(base["inicio"] + timedelta(hours=1)),
        },
        headers=_headers(token),
    )

    assert response.status_code == 409
    assert response.json()["codigo"] == "requiere_nueva_sena"
    assert await _contar_turnos(db_session) == 1
    await db_session.refresh(base["turno"])
    assert base["turno"].estado == "confirmado"


@pytest.mark.asyncio
async def test_segunda_reprogramacion_confirmada_cierra_el_viejo_y_crea_el_nuevo(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario(db_session, reprogramaciones_count=1)
    token = _token(base["clinic"].id, "recepcion")
    nuevo_inicio = base["inicio"] + timedelta(hours=1)

    response = await client.post(
        _reprogramar_url(base),
        json={
            "motivo": MOTIVO,
            "nuevo_inicio": _iso_utc(nuevo_inicio),
            "confirmar_perdida_sena": True,
        },
        headers=_headers(token),
    )

    assert response.status_code == 200
    body = response.json()
    await db_session.refresh(base["turno"])
    assert base["turno"].estado == "cancelado"
    assert base["turno"].sena_perdida is True
    assert base["turno"].estado != "reprogramado"

    assert body["id"] != str(base["turno"].id)
    assert body["estado"] == "pendiente_sena"
    assert body["reprogramado_de_id"] == str(base["turno"].id)
    assert body["reprogramaciones_count"] == 1
    assert datetime.fromisoformat(body["inicio"]) == nuevo_inicio.astimezone(UTC)
    assert await _contar_turnos(db_session) == 2


@pytest.mark.asyncio
async def test_endpoints_internos_en_openapi(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/internal/turnos/{turno_id}/cancelar" in paths
    assert "/api/internal/turnos/{turno_id}/reprogramar" in paths
