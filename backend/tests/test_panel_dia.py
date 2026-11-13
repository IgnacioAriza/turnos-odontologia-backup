"""Tests del panel del día y del marcado de ausentismo (C-07, grupo 5).

Fija el contrato de `GET /api/internal/panel/dia` y
`PATCH /api/internal/panel/turnos/{id}`: orden por hora, resumen, `estado_sena`,
contacto visible, máquina de estados idempotente y bloqueo transaccional por la
segunda falta (design D4/D5/D6).
"""

import asyncio
from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.clinica.models import Bloqueo
from app.domain.clinica.repository import BloqueoRepository
from app.domain.personas.models import Paciente
from app.domain.turnos import service
from app.domain.turnos.models import Turno
from app.infrastructure.db.base import get_async_session_factory
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

MARTES = date(2026, 1, 6)


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


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


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


async def _escenario_panel(db_session: AsyncSession) -> dict[str, object]:
    clinic = await crear_clinica(db_session)
    practica = await crear_practica(db_session, clinic, precio=Decimal("10000.00"))
    sillon = await crear_sillon(db_session, clinic, "Sillón 1")
    odonto_1 = await crear_odontologo(db_session, clinic)
    odonto_2 = await crear_odontologo(db_session, clinic)
    paciente_1 = await crear_paciente(
        db_session, clinic, nombre="Ana Paciente", telefono="+5491100000001"
    )
    paciente_2 = await crear_paciente(
        db_session, clinic, nombre="Beto Paciente", telefono="+5491100000002"
    )
    paciente_3 = await crear_paciente(
        db_session, clinic, nombre="Carla Paciente", telefono="+5491100000003"
    )
    paciente_cancelado = await crear_paciente(
        db_session, clinic, nombre="Dora Cancelada", telefono="+5491100000009"
    )

    turno_0900 = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente_1,
        sillon=sillon,
        odontologo=odonto_1,
        practica=practica,
        inicio=local(LUNES, time(9, 0)),
        estado="confirmado",
        monto_sena=Decimal("2000.00"),
    )
    turno_1030 = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente_2,
        sillon=sillon,
        odontologo=odonto_1,
        practica=practica,
        inicio=local(LUNES, time(10, 30)),
        estado="confirmado",
        monto_sena=Decimal("0.00"),
    )
    turno_1100 = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente_3,
        sillon=sillon,
        odontologo=odonto_2,
        practica=practica,
        inicio=local(LUNES, time(11, 0)),
        estado="pendiente_sena",
        monto_sena=Decimal("2000.00"),
    )
    turno_cancelado = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente_cancelado,
        sillon=sillon,
        odontologo=odonto_1,
        practica=practica,
        inicio=local(LUNES, time(12, 0)),
        estado="cancelado",
        monto_sena=Decimal("2000.00"),
    )
    turno_reprogramado = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente_2,
        sillon=sillon,
        odontologo=odonto_1,
        practica=practica,
        inicio=local(LUNES, time(13, 0)),
        estado="reprogramado",
        monto_sena=Decimal("2000.00"),
    )
    turno_completado = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente_1,
        sillon=sillon,
        odontologo=odonto_1,
        practica=practica,
        inicio=local(LUNES, time(14, 0)),
        estado="completado",
        monto_sena=Decimal("2000.00"),
        sena_perdida=True,
    )
    turno_ausente = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente_2,
        sillon=sillon,
        odontologo=odonto_2,
        practica=practica,
        inicio=local(LUNES, time(15, 0)),
        estado="ausente",
        monto_sena=Decimal("2000.00"),
    )
    return {
        "clinic": clinic,
        "practica": practica,
        "sillon": sillon,
        "odonto_1": odonto_1,
        "odonto_2": odonto_2,
        "paciente_1": paciente_1,
        "paciente_2": paciente_2,
        "paciente_3": paciente_3,
        "paciente_cancelado": paciente_cancelado,
        "turno_0900": turno_0900,
        "turno_1030": turno_1030,
        "turno_1100": turno_1100,
        "turno_cancelado": turno_cancelado,
        "turno_reprogramado": turno_reprogramado,
        "turno_completado": turno_completado,
        "turno_ausente": turno_ausente,
    }


async def _get_panel(client: AsyncClient, token: str, fecha: date = LUNES) -> dict[str, object]:
    response = await client.get(
        "/api/internal/panel/dia", params={"fecha": fecha.isoformat()}, headers=_headers(token)
    )
    assert response.status_code == 200, response.text
    return response.json()


def _ids(body: dict[str, object]) -> list[str]:
    return [str(turno["id"]) for turno in body["turnos"]]  # type: ignore[index]


def _por_id(body: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(turno["id"]): turno for turno in body["turnos"]}  # type: ignore[index]


async def _patch(client: AsyncClient, token: str, turno_id: UUID, estado: str) -> object:
    return await client.patch(
        f"/api/internal/panel/turnos/{turno_id}",
        json={"estado": estado},
        headers=_headers(token),
    )


# --- Listado del panel ---


@pytest.mark.asyncio
async def test_panel_ordena_por_hora_y_excluye_cancelado_y_reprogramado(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    body = await _get_panel(client, token)

    assert _ids(body) == [
        str(base["turno_0900"].id),  # type: ignore[attr-defined]
        str(base["turno_1030"].id),  # type: ignore[attr-defined]
        str(base["turno_1100"].id),  # type: ignore[attr-defined]
        str(base["turno_completado"].id),  # type: ignore[attr-defined]
        str(base["turno_ausente"].id),  # type: ignore[attr-defined]
    ]
    assert str(base["turno_cancelado"].id) not in _ids(body)  # type: ignore[attr-defined]
    assert str(base["turno_reprogramado"].id) not in _ids(body)  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_panel_incluye_paciente_practica_sillon_y_odontologo(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    turno = _por_id(await _get_panel(client, token))[str(base["turno_0900"].id)]  # type: ignore[attr-defined]

    assert turno["paciente"] == {
        "id": str(base["paciente_1"].id),  # type: ignore[attr-defined]
        "nombre": "Ana Paciente",
        "telefono": "+5491100000001",
    }
    assert turno["practica"]["nombre"] == "Limpieza"
    assert turno["sillon"]["nombre"] == "Sillón 1"
    assert turno["odontologo"]["email"] == base["odonto_1"].email  # type: ignore[attr-defined]
    assert turno["estado"] == "confirmado"


@pytest.mark.asyncio
async def test_panel_dia_vacio(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    body = await _get_panel(client, token, fecha=MARTES)

    assert body["turnos"] == []
    assert body["resumen"] == {
        "total": 0,
        "pendientes_sena": 0,
        "confirmados": 0,
        "completados": 0,
        "ausentes": 0,
    }


@pytest.mark.asyncio
async def test_resumen_de_la_jornada(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    body = await _get_panel(client, token)

    assert body["resumen"] == {
        "total": 5,
        "pendientes_sena": 1,
        "confirmados": 2,
        "completados": 1,
        "ausentes": 1,
    }


@pytest.mark.asyncio
async def test_estado_sena_cuatro_casos(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    turnos = _por_id(await _get_panel(client, token))

    assert turnos[str(base["turno_0900"].id)]["estado_sena"] == "aprobada"  # type: ignore[attr-defined]
    assert turnos[str(base["turno_1030"].id)]["estado_sena"] == "no_requerida"  # type: ignore[attr-defined]
    assert turnos[str(base["turno_1100"].id)]["estado_sena"] == "pendiente"  # type: ignore[attr-defined]
    assert turnos[str(base["turno_completado"].id)]["estado_sena"] == "perdida"  # type: ignore[attr-defined]
    assert turnos[str(base["turno_ausente"].id)]["estado_sena"] == "aprobada"  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_telefono_solo_de_turnos_del_panel(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    body = await _get_panel(client, token)

    assert "+5491100000001" in str(body)
    assert "+5491100000009" not in str(body)


@pytest.mark.asyncio
async def test_odonto_solo_ve_sus_turnos_y_su_contacto(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "odonto", sub=base["odonto_1"].id)  # type: ignore[attr-defined]

    body = await _get_panel(client, token)

    assert _ids(body) == [
        str(base["turno_0900"].id),  # type: ignore[attr-defined]
        str(base["turno_1030"].id),  # type: ignore[attr-defined]
        str(base["turno_completado"].id),  # type: ignore[attr-defined]
    ]
    assert "+5491100000003" not in str(body)


@pytest.mark.asyncio
async def test_panel_no_mezcla_clinicas(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario_panel(db_session)
    otra = await crear_clinica(db_session)
    otra_practica = await crear_practica(db_session, otra)
    otro_sillon = await crear_sillon(db_session, otra)
    otro_odonto = await crear_odontologo(db_session, otra)
    otro_paciente = await crear_paciente(
        db_session, otra, nombre="Paciente Ajeno", telefono="+5491188888888"
    )
    turno_ajeno = await crear_turno(
        db_session,
        clinic=otra,
        paciente=otro_paciente,
        sillon=otro_sillon,
        odontologo=otro_odonto,
        practica=otra_practica,
        inicio=local(LUNES, time(9, 0)),
        estado="confirmado",
    )
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    body = await _get_panel(client, token)

    assert str(turno_ajeno.id) not in _ids(body)
    assert "Paciente Ajeno" not in str(body)


# --- Marcado de completado y ausente ---


@pytest.mark.asyncio
async def test_marcar_completado_desde_confirmado(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    response = await _patch(client, token, base["turno_0900"].id, "completado")  # type: ignore[attr-defined]

    assert response.status_code == 200
    assert response.json()["estado"] == "completado"
    await db_session.refresh(base["paciente_1"])  # type: ignore[attr-defined]
    assert base["paciente_1"].faltas_count == 0  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_marcar_ausente_desde_confirmado_suma_una_falta(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    response = await _patch(client, token, base["turno_0900"].id, "ausente")  # type: ignore[attr-defined]

    assert response.status_code == 200
    assert response.json()["estado"] == "ausente"
    await db_session.refresh(base["paciente_1"])  # type: ignore[attr-defined]
    assert base["paciente_1"].faltas_count == 1  # type: ignore[attr-defined]
    assert base["paciente_1"].bloqueado_hasta is None  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_destino_invalido_422(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    response = await _patch(client, token, base["turno_0900"].id, "cancelado")  # type: ignore[attr-defined]

    assert response.status_code == 422
    await db_session.refresh(base["turno_0900"])  # type: ignore[attr-defined]
    assert base["turno_0900"].estado == "confirmado"  # type: ignore[attr-defined]


@pytest.mark.asyncio
@pytest.mark.parametrize("estado", ["pendiente_sena", "cancelado", "reprogramado"])
async def test_estados_no_actualizables_409(
    client: AsyncClient, db_session: AsyncSession, estado: str
) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]
    turno = await crear_turno(
        db_session,
        clinic=base["clinic"],  # type: ignore[arg-type]
        paciente=base["paciente_1"],  # type: ignore[arg-type]
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto_1"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=local(LUNES, time(16, 0)),
        estado=estado,
    )

    response = await _patch(client, token, turno.id, "ausente")

    assert response.status_code == 409
    assert response.json()["codigo"] == "estado_no_actualizable"
    await db_session.refresh(turno)
    assert turno.estado == estado


@pytest.mark.asyncio
async def test_turno_de_otra_clinica_404(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario_panel(db_session)
    otra = await crear_clinica(db_session)
    otra_practica = await crear_practica(db_session, otra)
    otro_sillon = await crear_sillon(db_session, otra)
    otro_odonto = await crear_odontologo(db_session, otra)
    otro_paciente = await crear_paciente(db_session, otra)
    turno_ajeno = await crear_turno(
        db_session,
        clinic=otra,
        paciente=otro_paciente,
        sillon=otro_sillon,
        odontologo=otro_odonto,
        practica=otra_practica,
        inicio=local(LUNES, time(9, 0)),
        estado="confirmado",
    )
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    response = await _patch(client, token, turno_ajeno.id, "completado")

    assert response.status_code == 404
    assert response.json()["codigo"] == "turno_no_encontrado"


@pytest.mark.asyncio
async def test_odonto_marca_su_turno_y_no_el_ajeno(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "odonto", sub=base["odonto_1"].id)  # type: ignore[attr-defined]

    ajeno = await _patch(client, token, base["turno_1100"].id, "completado")  # type: ignore[attr-defined]
    propio = await _patch(client, token, base["turno_0900"].id, "completado")  # type: ignore[attr-defined]

    assert ajeno.status_code == 404
    assert ajeno.json()["codigo"] == "turno_no_encontrado"
    assert propio.status_code == 200
    assert propio.json()["estado"] == "completado"


@pytest.mark.asyncio
async def test_ausente_repetido_es_idempotente(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    primera = await _patch(client, token, base["turno_0900"].id, "ausente")  # type: ignore[attr-defined]
    segunda = await _patch(client, token, base["turno_0900"].id, "ausente")  # type: ignore[attr-defined]

    assert primera.status_code == 200
    assert segunda.status_code == 200
    assert segunda.json()["estado"] == "ausente"
    await db_session.refresh(base["paciente_1"])  # type: ignore[attr-defined]
    assert base["paciente_1"].faltas_count == 1  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_completado_repetido_es_idempotente(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    primera = await _patch(client, token, base["turno_0900"].id, "completado")  # type: ignore[attr-defined]
    segunda = await _patch(client, token, base["turno_0900"].id, "completado")  # type: ignore[attr-defined]

    assert primera.status_code == 200
    assert segunda.status_code == 200
    assert segunda.json()["estado"] == "completado"


@pytest.mark.asyncio
async def test_pasar_de_ausente_a_completado_409(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_panel(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]
    await _patch(client, token, base["turno_0900"].id, "ausente")  # type: ignore[attr-defined]

    response = await _patch(client, token, base["turno_0900"].id, "completado")  # type: ignore[attr-defined]

    assert response.status_code == 409
    assert response.json()["codigo"] == "estado_no_actualizable"


# --- Bloqueo automático por segunda falta ---


@pytest.mark.asyncio
async def test_segunda_falta_crea_bloqueo_y_reinicia_contador(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_panel(db_session)
    paciente = base["paciente_1"]  # type: ignore[assignment]
    paciente.faltas_count = 1  # type: ignore[attr-defined]
    await db_session.flush()
    usuario_id = uuid4()
    token = _token(base["clinic"].id, "recepcion", sub=usuario_id)  # type: ignore[attr-defined]
    antes = datetime.now(UTC)

    response = await _patch(client, token, base["turno_0900"].id, "ausente")  # type: ignore[attr-defined]

    assert response.status_code == 200
    bloqueos = (
        (await db_session.execute(select(Bloqueo).where(Bloqueo.paciente_id == paciente.id)))
        .scalars()
        .all()
    )
    assert len(bloqueos) == 1
    bloqueo = bloqueos[0]
    assert bloqueo.motivo == "2_faltas"
    assert bloqueo.created_by == str(usuario_id)
    assert timedelta(days=29, hours=23) < _utc(bloqueo.hasta) - antes < timedelta(days=30, hours=1)
    await db_session.refresh(paciente)
    assert paciente.faltas_count == 0
    assert paciente.bloqueado_hasta is not None
    assert _utc(paciente.bloqueado_hasta) == _utc(bloqueo.hasta)


@pytest.mark.asyncio
async def test_falta_estando_bloqueado_extiende_el_bloqueo(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_panel(db_session)
    paciente = base["paciente_1"]  # type: ignore[assignment]
    viejo_hasta = datetime.now(UTC) + timedelta(days=10)
    paciente.bloqueado_hasta = viejo_hasta  # type: ignore[attr-defined]
    paciente.faltas_count = 1  # type: ignore[attr-defined]
    await db_session.flush()
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    response = await _patch(client, token, base["turno_0900"].id, "ausente")  # type: ignore[attr-defined]

    assert response.status_code == 200
    await db_session.refresh(paciente)
    assert paciente.faltas_count == 0
    assert paciente.bloqueado_hasta is not None
    assert _utc(paciente.bloqueado_hasta) > viejo_hasta + timedelta(days=19)
    bloqueos = (
        (await db_session.execute(select(Bloqueo).where(Bloqueo.paciente_id == paciente.id)))
        .scalars()
        .all()
    )
    assert len(bloqueos) == 1


@pytest.mark.asyncio
async def test_fallo_del_bloqueo_revierte_el_ausente(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    base = await _escenario_panel(db_session)
    paciente = base["paciente_1"]  # type: ignore[assignment]
    paciente.faltas_count = 1  # type: ignore[attr-defined]
    turno_id = base["turno_0900"].id  # type: ignore[attr-defined]
    paciente_id = paciente.id  # type: ignore[attr-defined]
    clinic_id = base["clinic"].id  # type: ignore[attr-defined]
    await db_session.flush()
    await db_session.commit()

    async def _crear_falla(self: BloqueoRepository, **kwargs: object) -> Bloqueo:
        raise RuntimeError("fallo simulado del bloqueo")

    monkeypatch.setattr(BloqueoRepository, "crear", _crear_falla)

    with pytest.raises(RuntimeError):
        await service.marcar_turno_panel(
            db_session,
            clinic_id=clinic_id,  # type: ignore[arg-type]
            turno_id=turno_id,  # type: ignore[arg-type]
            destino="ausente",
            usuario_id=uuid4(),
        )

    turno = await db_session.get(Turno, turno_id)
    assert turno is not None and turno.estado == "confirmado"
    paciente_db = await db_session.get(Paciente, paciente_id)
    assert paciente_db is not None and paciente_db.faltas_count == 1


@pytest.mark.asyncio
async def test_log_del_bloqueo_automatico(
    client: AsyncClient,
    db_session: AsyncSession,
    caplog: pytest.LogCaptureFixture,
) -> None:
    base = await _escenario_panel(db_session)
    paciente = base["paciente_1"]  # type: ignore[assignment]
    paciente.faltas_count = 1  # type: ignore[attr-defined]
    await db_session.flush()
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    with caplog.at_level("INFO"):
        response = await _patch(client, token, base["turno_0900"].id, "ausente")  # type: ignore[attr-defined]

    assert response.status_code == 200
    assert "bloqueo_automatico" in caplog.text


# --- La falta la marca una persona ---


@pytest.mark.asyncio
async def test_turno_vencido_sin_marcado_no_cambia(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_panel(db_session)
    vencido = await crear_turno(
        db_session,
        clinic=base["clinic"],  # type: ignore[arg-type]
        paciente=base["paciente_1"],  # type: ignore[arg-type]
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto_1"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=datetime.now(UTC) - timedelta(hours=2),
        estado="confirmado",
    )
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    await _get_panel(client, token)

    await db_session.refresh(vencido)
    await db_session.refresh(base["paciente_1"])  # type: ignore[attr-defined]
    assert vencido.estado == "confirmado"
    assert base["paciente_1"].faltas_count == 0  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_expiracion_de_sena_no_suma_falta(db_session: AsyncSession) -> None:
    base = await _escenario_panel(db_session)
    pendiente = await crear_turno(
        db_session,
        clinic=base["clinic"],  # type: ignore[arg-type]
        paciente=base["paciente_1"],  # type: ignore[arg-type]
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto_1"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=local(LUNES, time(17, 0)),
        estado="pendiente_sena",
        expira_at=datetime.now(UTC) - timedelta(minutes=5),
    )

    await service.expirar_pendientes(db_session, now=datetime.now(UTC))

    await db_session.refresh(pendiente)
    await db_session.refresh(base["paciente_1"])  # type: ignore[attr-defined]
    assert pendiente.estado == "cancelado"
    assert base["paciente_1"].faltas_count == 0  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_openapi_lista_panel_y_patch(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/internal/panel/dia" in paths
    assert "/api/internal/panel/turnos/{turno_id}" in paths


# --- Concurrencia real en Postgres (tarea 5.9) ---


@pytest.mark.skipif(
    "sqlite" in settings.database_url,
    reason="SELECT ... FOR UPDATE y concurrencia real requieren PostgreSQL",
)
@pytest.mark.asyncio
async def test_dos_ausentes_concurrentes_crean_un_solo_bloqueo(
    db_session: AsyncSession,
) -> None:
    base = await _escenario_panel(db_session)
    paciente = base["paciente_1"]  # type: ignore[assignment]
    paciente.faltas_count = 1  # type: ignore[attr-defined]
    segundo = await crear_turno(
        db_session,
        clinic=base["clinic"],  # type: ignore[arg-type]
        paciente=paciente,  # type: ignore[arg-type]
        sillon=base["sillon"],  # type: ignore[arg-type]
        odontologo=base["odonto_1"],  # type: ignore[arg-type]
        practica=base["practica"],  # type: ignore[arg-type]
        inicio=local(LUNES, time(18, 0)),
        estado="confirmado",
    )
    await db_session.commit()
    clinic_id = base["clinic"].id  # type: ignore[attr-defined]
    usuario_id = uuid4()
    factory = get_async_session_factory()

    async def _marcar(turno_id: UUID) -> None:
        async with factory() as session:
            await service.marcar_turno_panel(
                session,
                clinic_id=clinic_id,  # type: ignore[arg-type]
                turno_id=turno_id,
                destino="ausente",
                usuario_id=usuario_id,
            )

    await asyncio.gather(
        _marcar(base["turno_0900"].id),  # type: ignore[attr-defined]
        _marcar(segundo.id),
    )

    async with factory() as session:
        bloqueos = (
            (await session.execute(select(Bloqueo).where(Bloqueo.paciente_id == paciente.id)))
            .scalars()
            .all()
        )
        assert len(bloqueos) == 1
