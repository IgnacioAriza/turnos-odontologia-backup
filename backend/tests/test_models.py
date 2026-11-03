"""Tests para los modelos de dominio (Clinic, User, Paciente, Sillon, Bloqueo)."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clinica.models import Clinic, Sillon, Bloqueo
from app.domain.personas.models import User, Paciente


@pytest.mark.asyncio
async def test_clinic_model(db_session: AsyncSession):
    clinic = Clinic(
        nombre="Clínica Test",
        timezone="America/Argentina/Buenos_Aires",
        wa_sender="whatsapp:+5491100000000",
    )
    db_session.add(clinic)
    await db_session.flush()

    assert clinic.id is not None
    assert clinic.nombre == "Clínica Test"
    assert clinic.is_active is True
    assert clinic.created_at is not None
    assert clinic.updated_at is not None


@pytest.mark.asyncio
async def test_user_model(db_session: AsyncSession):
    clinic = Clinic(
        nombre="Clínica User Test",
        timezone="America/Argentina/Buenos_Aires",
    )
    db_session.add(clinic)
    await db_session.flush()

    user = User(
        clinic_id=clinic.id,
        email="test@clinica.com",
        password_hash="hashed_password",
        rol="recepcion",
        activo=True,
    )
    db_session.add(user)
    await db_session.flush()

    assert user.id is not None
    assert user.clinic_id == clinic.id
    assert user.email == "test@clinica.com"
    assert user.rol == "recepcion"
    assert user.activo is True


@pytest.mark.asyncio
async def test_paciente_model(db_session: AsyncSession):
    clinic = Clinic(
        nombre="Clínica Paciente Test",
        timezone="America/Argentina/Buenos_Aires",
    )
    db_session.add(clinic)
    await db_session.flush()

    paciente = Paciente(
        clinic_id=clinic.id,
        nombre="Juan Pérez",
        telefono="+5491100000000",
        dni="12345678",
    )
    db_session.add(paciente)
    await db_session.flush()

    assert paciente.id is not None
    assert paciente.clinic_id == clinic.id
    assert paciente.nombre == "Juan Pérez"
    assert paciente.telefono == "+5491100000000"
    assert paciente.dni == "12345678"


@pytest.mark.asyncio
async def test_sillon_model(db_session: AsyncSession):
    clinic = Clinic(
        nombre="Clínica Sillon Test",
        timezone="America/Argentina/Buenos_Aires",
    )
    db_session.add(clinic)
    await db_session.flush()

    sillon = Sillon(
        clinic_id=clinic.id,
        nombre="Sillón 1",
        activo=True,
    )
    db_session.add(sillon)
    await db_session.flush()

    assert sillon.id is not None
    assert sillon.clinic_id == clinic.id
    assert sillon.nombre == "Sillón 1"
    assert sillon.activo is True


@pytest.mark.asyncio
async def test_bloqueo_model(db_session: AsyncSession):
    clinic = Clinic(
        nombre="Clínica Bloqueo Test",
        timezone="America/Argentina/Buenos_Aires",
    )
    db_session.add(clinic)
    await db_session.flush()

    paciente = Paciente(
        clinic_id=clinic.id,
        nombre="Paciente Bloqueado",
        telefono="+5491100000001",
        dni="87654321",
    )
    db_session.add(paciente)
    await db_session.flush()

    from datetime import datetime, timedelta
    desde = datetime(2026, 11, 1, 10, 0, 0)
    hasta = desde + timedelta(days=30)

    bloqueo = Bloqueo(
        clinic_id=clinic.id,
        paciente_id=paciente.id,
        desde=desde,
        hasta=hasta,
        motivo="2_faltas",
        created_by="recepcion@clinica.com",
    )
    db_session.add(bloqueo)
    await db_session.flush()

    assert bloqueo.id is not None
    assert bloqueo.clinic_id == clinic.id
    assert bloqueo.paciente_id == paciente.id
    assert bloqueo.motivo == "2_faltas"


@pytest.mark.asyncio
async def test_email_unique_per_clinic(db_session: AsyncSession):
    """El email debe ser único por clínica."""
    clinic1 = Clinic(nombre="Clínica A", timezone="America/Argentina/Buenos_Aires")
    clinic2 = Clinic(nombre="Clínica B", timezone="America/Argentina/Buenos_Aires")
    db_session.add_all([clinic1, clinic2])
    await db_session.flush()

    user1 = User(
        clinic_id=clinic1.id,
        email="same@email.com",
        password_hash="hash1",
        rol="admin",
    )
    user2 = User(
        clinic_id=clinic2.id,
        email="same@email.com",
        password_hash="hash2",
        rol="admin",
    )
    db_session.add_all([user1, user2])
    await db_session.flush()

    # Mismo email en clínicas diferentes debe ser válido
    assert user1.id is not None
    assert user2.id is not None

    # Mismo email en la misma clínica debe fallar (constraint UNIQUE)
    user3 = User(
        clinic_id=clinic1.id,
        email="same@email.com",
        password_hash="hash3",
        rol="recepcion",
    )
    db_session.add(user3)
    with pytest.raises(Exception):
        await db_session.flush()
