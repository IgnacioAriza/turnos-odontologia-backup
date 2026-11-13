"""Tests de la agenda operativa y del catálogo de odontólogos (C-07, grupo 4).

Cubre el contrato de `GET /api/internal/agenda`: rangos día/semana en la zona
de la clínica, filtros combinables, exclusión de cancelados, orden estable,
aislamiento por clínica y confinamiento del odontólogo (design D2/D3).
"""

from collections.abc import AsyncGenerator
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import text
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

MARTES = date(2026, 1, 6)
MIERCOLES = date(2026, 1, 7)
LUNES_ANTERIOR = date(2025, 12, 29)


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


async def _escenario_agenda(db_session: AsyncSession) -> dict[str, object]:
    clinic = await crear_clinica(db_session)
    practica = await crear_practica(db_session, clinic, precio=Decimal("10000.00"))
    sillon_1 = await crear_sillon(db_session, clinic, "Sillón 1")
    sillon_2 = await crear_sillon(db_session, clinic, "Sillón 2")
    odonto_1 = await crear_odontologo(db_session, clinic)
    odonto_2 = await crear_odontologo(db_session, clinic)
    paciente_1 = await crear_paciente(db_session, clinic, nombre="Ana Paciente")
    paciente_2 = await crear_paciente(db_session, clinic, nombre="Beto Paciente")

    turno_0900_s1 = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente_1,
        sillon=sillon_1,
        odontologo=odonto_1,
        practica=practica,
        inicio=local(LUNES, time(9, 0)),
        estado="confirmado",
    )
    turno_0900_s2 = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente_2,
        sillon=sillon_2,
        odontologo=odonto_2,
        practica=practica,
        inicio=local(LUNES, time(9, 0)),
        estado="confirmado",
    )
    turno_1000 = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente_1,
        sillon=sillon_1,
        odontologo=odonto_2,
        practica=practica,
        inicio=local(LUNES, time(10, 0)),
        estado="pendiente_sena",
    )
    turno_cancelado = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente_2,
        sillon=sillon_1,
        odontologo=odonto_1,
        practica=practica,
        inicio=local(LUNES, time(11, 0)),
        estado="cancelado",
    )
    turno_martes = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente_1,
        sillon=sillon_1,
        odontologo=odonto_1,
        practica=practica,
        inicio=local(MARTES, time(9, 0)),
        estado="confirmado",
    )
    turno_semana_anterior = await crear_turno(
        db_session,
        clinic=clinic,
        paciente=paciente_1,
        sillon=sillon_1,
        odontologo=odonto_1,
        practica=practica,
        inicio=local(LUNES_ANTERIOR, time(9, 0)),
        estado="confirmado",
    )
    return {
        "clinic": clinic,
        "practica": practica,
        "sillon_1": sillon_1,
        "sillon_2": sillon_2,
        "odonto_1": odonto_1,
        "odonto_2": odonto_2,
        "paciente_1": paciente_1,
        "paciente_2": paciente_2,
        "turno_0900_s1": turno_0900_s1,
        "turno_0900_s2": turno_0900_s2,
        "turno_1000": turno_1000,
        "turno_cancelado": turno_cancelado,
        "turno_martes": turno_martes,
        "turno_semana_anterior": turno_semana_anterior,
    }


async def _get_agenda(client: AsyncClient, token: str, **params: str) -> dict[str, object]:
    response = await client.get("/api/internal/agenda", params=params, headers=_headers(token))
    assert response.status_code == 200, response.text
    return response.json()


def _ids(body: dict[str, object]) -> list[str]:
    return [str(turno["id"]) for turno in body["turnos"]]  # type: ignore[index]


@pytest.mark.asyncio
async def test_vista_dia_devuelve_solo_los_turnos_del_dia(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_agenda(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    body = await _get_agenda(client, token, vista="dia", fecha=LUNES.isoformat())

    assert body["vista"] == "dia"
    assert datetime.fromisoformat(str(body["desde"])) == local(LUNES, time.min)
    assert datetime.fromisoformat(str(body["hasta"])) == local(LUNES + timedelta(days=1), time.min)
    ids = _ids(body)
    assert str(base["turno_0900_s1"].id) in ids  # type: ignore[attr-defined]
    assert str(base["turno_0900_s2"].id) in ids  # type: ignore[attr-defined]
    assert str(base["turno_1000"].id) in ids  # type: ignore[attr-defined]
    assert str(base["turno_martes"].id) not in ids  # type: ignore[attr-defined]
    assert str(base["turno_semana_anterior"].id) not in ids  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_vista_semana_va_de_lunes_a_domingo(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_agenda(db_session)
    token = _token(base["clinic"].id, "admin")  # type: ignore[attr-defined]

    body = await _get_agenda(client, token, vista="semana", fecha=MIERCOLES.isoformat())

    assert body["vista"] == "semana"
    assert datetime.fromisoformat(str(body["desde"])) == local(LUNES, time.min)
    assert datetime.fromisoformat(str(body["hasta"])) == local(LUNES + timedelta(days=7), time.min)
    ids = _ids(body)
    assert str(base["turno_martes"].id) in ids  # type: ignore[attr-defined]
    assert str(base["turno_semana_anterior"].id) not in ids  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_orden_estable_por_inicio_sillon_y_odontologo(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_agenda(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    primero = _ids(await _get_agenda(client, token, vista="dia", fecha=LUNES.isoformat()))
    segundo = _ids(await _get_agenda(client, token, vista="dia", fecha=LUNES.isoformat()))

    assert primero == segundo
    assert primero == [
        str(base["turno_0900_s1"].id),  # type: ignore[attr-defined]
        str(base["turno_0900_s2"].id),  # type: ignore[attr-defined]
        str(base["turno_1000"].id),  # type: ignore[attr-defined]
    ]


@pytest.mark.asyncio
async def test_filtro_por_sillon(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario_agenda(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    body = await _get_agenda(
        client,
        token,
        vista="dia",
        fecha=LUNES.isoformat(),
        sillon=str(base["sillon_2"].id),  # type: ignore[attr-defined]
    )

    assert _ids(body) == [str(base["turno_0900_s2"].id)]  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_filtro_por_odontologo(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario_agenda(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    body = await _get_agenda(
        client,
        token,
        vista="dia",
        fecha=LUNES.isoformat(),
        odontologo=str(base["odonto_2"].id),  # type: ignore[attr-defined]
    )

    assert _ids(body) == [str(base["turno_0900_s2"].id), str(base["turno_1000"].id)]  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_filtro_por_estado(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario_agenda(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    body = await _get_agenda(
        client, token, vista="dia", fecha=LUNES.isoformat(), estado="pendiente_sena"
    )

    assert _ids(body) == [str(base["turno_1000"].id)]  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_cancelado_excluido_por_defecto_e_incluido_si_se_pide(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_agenda(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    por_defecto = await _get_agenda(client, token, vista="dia", fecha=LUNES.isoformat())
    solo_cancelados = await _get_agenda(
        client, token, vista="dia", fecha=LUNES.isoformat(), estado="cancelado"
    )

    assert str(base["turno_cancelado"].id) not in _ids(por_defecto)  # type: ignore[attr-defined]
    assert _ids(solo_cancelados) == [str(base["turno_cancelado"].id)]  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_dia_vacio_devuelve_lista_y_rango(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_agenda(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]
    vacio = date(2026, 2, 10)

    body = await _get_agenda(client, token, vista="dia", fecha=vacio.isoformat())

    assert body["turnos"] == []
    assert datetime.fromisoformat(str(body["desde"])) == local(vacio, time.min)


@pytest.mark.asyncio
async def test_filtros_combinados_sin_resultados(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_agenda(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    body = await _get_agenda(
        client,
        token,
        vista="dia",
        fecha=LUNES.isoformat(),
        sillon=str(base["sillon_2"].id),  # type: ignore[attr-defined]
        estado="pendiente_sena",
    )

    assert body["turnos"] == []


@pytest.mark.asyncio
async def test_vista_invalida_422(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario_agenda(db_session)
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    response = await client.get(
        "/api/internal/agenda",
        params={"vista": "mes", "fecha": LUNES.isoformat()},
        headers=_headers(token),
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_turnos_de_otra_clinica_no_aparecen(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_agenda(db_session)
    otra = await crear_clinica(db_session)
    otra_practica = await crear_practica(db_session, otra)
    otro_sillon = await crear_sillon(db_session, otra)
    otro_odonto = await crear_odontologo(db_session, otra)
    otro_paciente = await crear_paciente(db_session, otra, nombre="Paciente Ajeno")
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

    body = await _get_agenda(client, token, vista="dia", fecha=LUNES.isoformat())

    assert str(turno_ajeno.id) not in _ids(body)
    assert "Paciente Ajeno" not in str(body)


@pytest.mark.asyncio
async def test_filtro_con_sillon_de_otra_clinica_devuelve_vacio(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_agenda(db_session)
    otra = await crear_clinica(db_session)
    sillon_ajeno = await crear_sillon(db_session, otra, "Sillón Ajeno")
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    body = await _get_agenda(
        client, token, vista="dia", fecha=LUNES.isoformat(), sillon=str(sillon_ajeno.id)
    )

    assert body["turnos"] == []


@pytest.mark.asyncio
async def test_odonto_solo_ve_sus_turnos(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario_agenda(db_session)
    token = _token(base["clinic"].id, "odonto", sub=base["odonto_1"].id)  # type: ignore[attr-defined]

    body = await _get_agenda(client, token, vista="dia", fecha=LUNES.isoformat())

    assert _ids(body) == [str(base["turno_0900_s1"].id)]  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_odonto_ignora_el_filtro_de_otro_odontologo(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_agenda(db_session)
    token = _token(base["clinic"].id, "odonto", sub=base["odonto_1"].id)  # type: ignore[attr-defined]

    body = await _get_agenda(
        client,
        token,
        vista="dia",
        fecha=LUNES.isoformat(),
        odontologo=str(base["odonto_2"].id),  # type: ignore[attr-defined]
    )

    assert _ids(body) == [str(base["turno_0900_s1"].id)]  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_recepcion_y_admin_ven_todos_los_odontologos(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_agenda(db_session)

    for rol in ("recepcion", "admin"):
        token = _token(base["clinic"].id, rol)  # type: ignore[attr-defined]
        body = await _get_agenda(client, token, vista="dia", fecha=LUNES.isoformat())
        assert len(_ids(body)) == 3


@pytest.mark.asyncio
async def test_rol_no_interno_403(client: AsyncClient, db_session: AsyncSession) -> None:
    base = await _escenario_agenda(db_session)
    token = _token(base["clinic"].id, "paciente")  # type: ignore[attr-defined]

    response = await client.get(
        "/api/internal/agenda",
        params={"vista": "dia", "fecha": LUNES.isoformat()},
        headers=_headers(token),
    )

    assert response.status_code == 403


@pytest.mark.asyncio
async def test_openapi_lista_agenda_con_query_params(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    params = response.json()["paths"]["/api/internal/agenda"]["get"]["parameters"]
    nombres = {param["name"] for param in params}
    assert {"vista", "fecha", "sillon", "odontologo", "estado"} <= nombres


# --- Catálogo de odontólogos para los filtros (tarea 4.5) ---


@pytest.mark.asyncio
async def test_lista_odontologos_solo_activos_de_la_clinica(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_agenda(db_session)
    inactivo = await crear_odontologo(db_session, base["clinic"])  # type: ignore[arg-type]
    inactivo.activo = False
    otra = await crear_clinica(db_session)
    await crear_odontologo(db_session, otra)
    await db_session.flush()
    token = _token(base["clinic"].id, "recepcion")  # type: ignore[attr-defined]

    response = await client.get("/api/internal/odontologos", headers=_headers(token))

    assert response.status_code == 200
    body = response.json()
    emails = [item["email"] for item in body]
    assert emails == sorted(emails)
    assert str(base["odonto_1"].email) in emails  # type: ignore[attr-defined]
    assert str(base["odonto_2"].email) in emails  # type: ignore[attr-defined]
    assert inactivo.email not in emails
    assert all(item["id"] for item in body)


@pytest.mark.asyncio
async def test_lista_odontologos_requiere_rol_interno(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_agenda(db_session)
    token = _token(base["clinic"].id, "paciente")  # type: ignore[attr-defined]

    response = await client.get("/api/internal/odontologos", headers=_headers(token))

    assert response.status_code == 403


# --- Plan de consulta en Postgres (tarea 4.6) ---


@pytest.mark.skipif(
    "sqlite" in settings.database_url,
    reason="EXPLAIN (ANALYZE, BUFFERS) requiere PostgreSQL",
)
@pytest.mark.asyncio
async def test_explain_agenda_semana_no_hace_seq_scan(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    base = await _escenario_agenda(db_session)
    desde = local(LUNES, time.min).astimezone(UTC)
    hasta = local(LUNES + timedelta(days=7), time.min).astimezone(UTC)

    plan = (
        (
            await db_session.execute(
                text(
                    "EXPLAIN (ANALYZE, BUFFERS) "
                    "SELECT * FROM turnos "
                    "WHERE clinic_id = :clinic_id AND inicio >= :desde AND inicio < :hasta "
                    "AND estado <> 'cancelado'"
                ),
                {"clinic_id": str(base["clinic"].id), "desde": desde, "hasta": hasta},  # type: ignore[attr-defined]
            )
        )
        .scalars()
        .all()
    )

    detalle = "\n".join(plan)
    assert "Seq Scan on turnos" not in detalle, detalle
