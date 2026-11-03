"""Tests para clinic_id obligatorio en todas las tablas de negocio."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clinica.models import Bloqueo, Sillon
from app.domain.personas.models import Paciente, User


@pytest.mark.skipif(
    "sqlite" in __import__("app.core.config", fromlist=["settings"]).settings.database_url,
    reason="Requires PostgreSQL for NOT NULL and FK constraints",
)
@pytest.mark.asyncio
async def test_clinic_id_required_on_users(db_session: AsyncSession):
    """users.clinic_id es NOT NULL."""
    user = User(
        email="no_clinic@test.com",
        password_hash="hash",
        rol="admin",
    )
    db_session.add(user)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.skipif(
    "sqlite" in __import__("app.core.config", fromlist=["settings"]).settings.database_url,
    reason="Requires PostgreSQL for NOT NULL and FK constraints",
)
@pytest.mark.asyncio
async def test_clinic_id_required_on_pacientes(db_session: AsyncSession):
    """pacientes.clinic_id es NOT NULL."""
    paciente = Paciente(
        nombre="Sin Clinica",
        telefono="+5491100000002",
        dni="99999999",
    )
    db_session.add(paciente)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.skipif(
    "sqlite" in __import__("app.core.config", fromlist=["settings"]).settings.database_url,
    reason="Requires PostgreSQL for NOT NULL and FK constraints",
)
@pytest.mark.asyncio
async def test_clinic_id_required_on_sillones(db_session: AsyncSession):
    """sillones.clinic_id es NOT NULL."""
    sillon = Sillon(
        nombre="Sin Clinica",
    )
    db_session.add(sillon)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.skipif(
    "sqlite" in __import__("app.core.config", fromlist=["settings"]).settings.database_url,
    reason="Requires PostgreSQL for NOT NULL and FK constraints",
)
@pytest.mark.asyncio
async def test_clinic_id_required_on_bloqueos(db_session: AsyncSession):
    """bloqueos.clinic_id es NOT NULL."""
    bloqueo = Bloqueo(
        paciente_id=None,
        desde=None,
        hasta=None,
        motivo="test",
    )
    db_session.add(bloqueo)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.skipif(
    "sqlite" in __import__("app.core.config", fromlist=["settings"]).settings.database_url,
    reason="Requires PostgreSQL for FK constraints",
)
@pytest.mark.asyncio
async def test_clinic_fk_constraint(db_session: AsyncSession):
    """clinic_id debe referenciar a clinic.id válido."""
    from uuid import uuid4

    sillon = Sillon(
        clinic_id=uuid4(),  # UUID inexistente
        nombre="FK Test",
    )
    db_session.add(sillon)
    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()
