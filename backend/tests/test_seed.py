"""Tests para el script de seed idempotente."""

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clinica.models import Clinic, Sillon
from app.domain.personas.models import User


@pytest.mark.skipif(
    "sqlite" in __import__("app.core.config", fromlist=["settings"]).settings.database_url,
    reason="Requires PostgreSQL for seed script",
)
@pytest.mark.asyncio
async def test_seed_creates_clinic(db_session: AsyncSession):
    """El seed debe crear exactamente 1 clínica."""
    from backend.scripts.seed import seed

    await seed()

    result = await db_session.execute(select(Clinic))
    clinics = result.scalars().all()
    assert len(clinics) == 1
    assert clinics[0].timezone == "America/Argentina/Buenos_Aires"


@pytest.mark.skipif(
    "sqlite" in __import__("app.core.config", fromlist=["settings"]).settings.database_url,
    reason="Requires PostgreSQL for seed script",
)
@pytest.mark.asyncio
async def test_seed_creates_users(db_session: AsyncSession):
    """El seed debe crear admin, recepcion y odontólogo."""
    from backend.scripts.seed import seed

    await seed()

    result = await db_session.execute(select(User))
    users = result.scalars().all()
    roles = {u.rol for u in users}
    assert "admin" in roles
    assert "recepcion" in roles
    assert "odonto" in roles


@pytest.mark.skipif(
    "sqlite" in __import__("app.core.config", fromlist=["settings"]).settings.database_url,
    reason="Requires PostgreSQL for seed script",
)
@pytest.mark.asyncio
async def test_seed_creates_sillones(db_session: AsyncSession):
    """El seed debe crear 2-3 sillones activos."""
    from backend.scripts.seed import seed

    await seed()

    result = await db_session.execute(select(Sillon))
    sillones = result.scalars().all()
    assert 2 <= len(sillones) <= 3
    assert all(s.activo for s in sillones)


@pytest.mark.skipif(
    "sqlite" in __import__("app.core.config", fromlist=["settings"]).settings.database_url,
    reason="Requires PostgreSQL for seed script",
)
@pytest.mark.asyncio
async def test_seed_idempotent(db_session: AsyncSession):
    """Ejecutar seed dos veces no debe duplicar datos."""
    from backend.scripts.seed import seed

    await seed()
    await seed()

    result = await db_session.execute(select(Clinic))
    clinics = result.scalars().all()
    assert len(clinics) == 1

    result = await db_session.execute(select(User))
    users = result.scalars().all()
    emails = {u.email for u in users}
    assert emails == {"admin@clinica.com", "recepcion@clinica.com", "odontologo@clinica.com"}
