"""Tests para el script de seed idempotente."""

import importlib.util
from datetime import time
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clinica.models import Arancel, Clinic, Sillon, TipoPractica
from app.domain.personas.models import User
from app.domain.turnos.models import HorarioAtencion

SEED_PATH = Path(__file__).resolve().parents[1] / "scripts" / "seed.py"


def _load_seed():
    """Cargar el script de seed por ruta para no depender del paquete `backend`."""
    spec = importlib.util.spec_from_file_location("seed_c04", SEED_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


@pytest.mark.asyncio
async def test_seed_creates_cinco_practicas(db_session: AsyncSession):
    """El seed crea las cinco prácticas y sus cinco aranceles."""
    seed = _load_seed().seed

    await seed()

    result = await db_session.execute(select(TipoPractica))
    practicas = list(result.scalars().all())
    nombres = {p.nombre for p in practicas}

    assert len(practicas) == 5
    assert nombres == {"Limpieza", "Arreglo", "Endodoncia", "Extracción", "Ortodoncia control"}

    result = await db_session.execute(select(Arancel))
    aranceles = list(result.scalars().all())
    assert len(aranceles) == 5


@pytest.mark.asyncio
async def test_seed_practicas_idempotente(db_session: AsyncSession):
    """Correr el seed dos veces no duplica prácticas ni aranceles."""
    seed = _load_seed().seed

    await seed()
    await seed()

    result = await db_session.execute(select(TipoPractica))
    assert len(list(result.scalars().all())) == 5

    result = await db_session.execute(select(Arancel))
    assert len(list(result.scalars().all())) == 5


@pytest.mark.asyncio
async def test_seed_cada_practica_tiene_su_arancel(db_session: AsyncSession):
    """Cada práctica queda con un arancel 1:1 y los mismos valores del seed."""
    seed = _load_seed().seed

    await seed()

    result = await db_session.execute(select(TipoPractica))
    practicas = list(result.scalars().all())
    assert len(practicas) == 5

    for practica in practicas:
        result = await db_session.execute(
            select(Arancel).where(Arancel.tipo_practica_id == practica.id)
        )
        arancel = result.scalar_one_or_none()
        assert arancel is not None
        assert arancel.precio == practica.precio_base
        assert arancel.sena_pct == practica.sena_pct


@pytest.mark.asyncio
async def test_seed_crea_horarios_de_atencion(db_session: AsyncSession):
    """El seed deja L-V 08:00-20:00 y sábado 08:00-13:00, sin domingo."""
    seed = _load_seed().seed

    await seed()

    result = await db_session.execute(select(HorarioAtencion))
    horarios = list(result.scalars().all())

    assert len(horarios) == 6
    por_dia = {horario.dia_semana: horario for horario in horarios}
    assert set(por_dia) == {0, 1, 2, 3, 4, 5}
    for dia in range(5):
        assert por_dia[dia].hora_desde == time(8, 0)
        assert por_dia[dia].hora_hasta == time(20, 0)
    assert por_dia[5].hora_desde == time(8, 0)
    assert por_dia[5].hora_hasta == time(13, 0)
    assert all(horario.activo for horario in horarios)


@pytest.mark.asyncio
async def test_seed_horarios_idempotente(db_session: AsyncSession):
    """Correr el seed dos veces no duplica horarios."""
    seed = _load_seed().seed

    await seed()
    await seed()

    result = await db_session.execute(select(HorarioAtencion))
    assert len(list(result.scalars().all())) == 6
