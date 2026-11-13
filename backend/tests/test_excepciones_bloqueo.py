"""Tests del modelo y repositorio `ExcepcionBloqueo` (C-07, tareas 2.3 / 2.4)."""

from datetime import time
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clinica.models import ExcepcionBloqueo
from app.domain.clinica.repository import ExcepcionBloqueoRepository
from app.domain.personas.models import User
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


async def _usuario_recepcion(db: AsyncSession, clinic_id) -> User:
    usuario = User(
        clinic_id=clinic_id,
        email=f"recepcion-{uuid4().hex[:8]}@clinica.com",
        password_hash="x",
        rol="recepcion",
        activo=True,
        is_active=True,
    )
    db.add(usuario)
    await db.flush()
    return usuario


async def _escenario(db: AsyncSession) -> dict[str, object]:
    clinic = await crear_clinica(db)
    practica = await crear_practica(db, clinic)
    sillon = await crear_sillon(db, clinic)
    odonto = await crear_odontologo(db, clinic)
    paciente = await crear_paciente(db, clinic)
    usuario = await _usuario_recepcion(db, clinic.id)
    turno = await crear_turno(
        db,
        clinic=clinic,
        paciente=paciente,
        sillon=sillon,
        odontologo=odonto,
        practica=practica,
        inicio=local(LUNES, time(9, 0)),
    )
    return {
        "clinic": clinic,
        "paciente": paciente,
        "turno": turno,
        "usuario": usuario,
    }


@pytest.mark.asyncio
async def test_modelo_mapea_columnas_de_auditoria(db_session: AsyncSession) -> None:
    base = await _escenario(db_session)

    excepcion = ExcepcionBloqueo(
        clinic_id=base["clinic"].id,  # type: ignore[attr-defined]
        paciente_id=base["paciente"].id,  # type: ignore[attr-defined]
        turno_id=base["turno"].id,  # type: ignore[attr-defined]
        usuario_id=base["usuario"].id,  # type: ignore[attr-defined]
        motivo="Paciente con urgencia",
        is_active=True,
    )
    db_session.add(excepcion)
    await db_session.flush()
    await db_session.refresh(excepcion)

    assert excepcion.id is not None
    assert excepcion.clinic_id == base["clinic"].id  # type: ignore[attr-defined]
    assert excepcion.paciente_id == base["paciente"].id  # type: ignore[attr-defined]
    assert excepcion.turno_id == base["turno"].id  # type: ignore[attr-defined]
    assert excepcion.usuario_id == base["usuario"].id  # type: ignore[attr-defined]
    assert excepcion.motivo == "Paciente con urgencia"
    assert excepcion.created_at is not None
    assert excepcion.is_active is True


@pytest.mark.asyncio
async def test_clinic_id_es_obligatorio(db_session: AsyncSession) -> None:
    base = await _escenario(db_session)

    db_session.add(
        ExcepcionBloqueo(
            clinic_id=None,
            paciente_id=base["paciente"].id,  # type: ignore[attr-defined]
            turno_id=base["turno"].id,  # type: ignore[attr-defined]
            usuario_id=base["usuario"].id,  # type: ignore[attr-defined]
            motivo="Sin clínica",
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_un_turno_admite_una_sola_excepcion(db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    datos = {
        "clinic_id": base["clinic"].id,  # type: ignore[attr-defined]
        "paciente_id": base["paciente"].id,  # type: ignore[attr-defined]
        "turno_id": base["turno"].id,  # type: ignore[attr-defined]
        "usuario_id": base["usuario"].id,  # type: ignore[attr-defined]
    }

    db_session.add(ExcepcionBloqueo(**datos, motivo="Primera"))
    await db_session.flush()
    db_session.add(ExcepcionBloqueo(**datos, motivo="Duplicada"))

    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_repositorio_crea_y_consulta_por_turno(db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    repo = ExcepcionBloqueoRepository(db_session)

    creada = await repo.crear(
        clinic_id=base["clinic"].id,  # type: ignore[attr-defined]
        paciente_id=base["paciente"].id,  # type: ignore[attr-defined]
        turno_id=base["turno"].id,  # type: ignore[attr-defined]
        usuario_id=base["usuario"].id,  # type: ignore[attr-defined]
        motivo="Excepción de mostrador",
    )
    await db_session.commit()

    assert creada.id is not None
    encontrada = await repo.get_by_turno(base["turno"].id)  # type: ignore[attr-defined]
    assert encontrada is not None
    assert encontrada.motivo == "Excepción de mostrador"


@pytest.mark.asyncio
async def test_repositorio_aisla_por_clinica(db_session: AsyncSession) -> None:
    base = await _escenario(db_session)
    otra = await _escenario(db_session)
    repo = ExcepcionBloqueoRepository(db_session)

    await repo.crear(
        clinic_id=base["clinic"].id,  # type: ignore[attr-defined]
        paciente_id=base["paciente"].id,  # type: ignore[attr-defined]
        turno_id=base["turno"].id,  # type: ignore[attr-defined]
        usuario_id=base["usuario"].id,  # type: ignore[attr-defined]
        motivo="Propia",
    )
    await repo.crear(
        clinic_id=otra["clinic"].id,  # type: ignore[attr-defined]
        paciente_id=otra["paciente"].id,  # type: ignore[attr-defined]
        turno_id=otra["turno"].id,  # type: ignore[attr-defined]
        usuario_id=otra["usuario"].id,  # type: ignore[attr-defined]
        motivo="Ajena",
    )
    await db_session.commit()

    propias = await repo.list_by_clinic(base["clinic"].id)  # type: ignore[attr-defined]

    assert [e.motivo for e in propias] == ["Propia"]
    assert propias[0].clinic_id == base["clinic"].id  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_modelo_importable_desde_clinica() -> None:
    """El modelo vive en `clinica.models` para compartir el dominio de bloqueos."""
    from app.domain.clinica import models

    assert models.ExcepcionBloqueo is ExcepcionBloqueo
