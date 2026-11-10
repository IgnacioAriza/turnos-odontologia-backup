"""Tests para la resolución de precio efectivo y los repositorios del catálogo."""

from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clinica.models import Arancel, Clinic, TipoPractica
from app.domain.clinica.repository import ArancelRepository, TipoPracticaRepository
from app.domain.personas import models as _personas_models  # noqa: F401


def _tipo(precio_base: str = "15000.00") -> TipoPractica:
    return TipoPractica(
        nombre="Limpieza", duracion_min=30, precio_base=Decimal(precio_base), sena_pct=30
    )


def _arancel(vigente_desde: date, precio: str = "25000.00") -> Arancel:
    return Arancel(precio=Decimal(precio), sena_pct=40, vigente_desde=vigente_desde)


def test_precio_efectivo_usa_arancel_vigente():
    """Con arancel vigente a la fecha, gana el precio del arancel."""
    from app.domain.clinica.catalogo_service import precio_efectivo

    tipo = _tipo("15000.00")
    arancel = _arancel(date(2026, 1, 1), "25000.00")

    assert precio_efectivo(tipo, arancel, date(2026, 6, 1)) == Decimal("25000.00")


def test_precio_efectivo_ignora_arancel_futuro():
    """Un arancel que todavía no rige cae al precio base."""
    from app.domain.clinica.catalogo_service import precio_efectivo

    tipo = _tipo("15000.00")
    arancel = _arancel(date(2027, 1, 1), "25000.00")

    assert precio_efectivo(tipo, arancel, date(2026, 6, 1)) == Decimal("15000.00")


def test_precio_efectivo_sin_arancel():
    """Sin arancel, el precio efectivo es el precio base."""
    from app.domain.clinica.catalogo_service import precio_efectivo

    tipo = _tipo("18000.00")

    assert precio_efectivo(tipo, None, date(2026, 6, 1)) == Decimal("18000.00")


def test_precio_efectivo_arancel_que_rige_hoy():
    """Si el arancel rige exactamente hoy, se usa."""
    from app.domain.clinica.catalogo_service import precio_efectivo

    tipo = _tipo("15000.00")
    hoy = date(2026, 6, 1)

    assert precio_efectivo(tipo, _arancel(hoy, "33000.00"), hoy) == Decimal("33000.00")


async def _crear_clinic(db_session: AsyncSession, nombre: str) -> Clinic:
    clinic = Clinic(nombre=nombre, timezone="America/Argentina/Buenos_Aires")
    db_session.add(clinic)
    await db_session.flush()
    return clinic


@pytest.mark.asyncio
async def test_repositorio_tipos_filtra_por_clinic(db_session: AsyncSession):
    """TipoPracticaRepository.list_activas no devuelve prácticas de otra clínica."""
    clinic_a = await _crear_clinic(db_session, "Clínica Repo A")
    clinic_b = await _crear_clinic(db_session, "Clínica Repo B")
    db_session.add(
        TipoPractica(
            clinic_id=clinic_a.id,
            nombre="Limpieza",
            duracion_min=30,
            precio_base=Decimal("15000.00"),
            sena_pct=30,
        )
    )
    db_session.add(
        TipoPractica(
            clinic_id=clinic_b.id,
            nombre="Endodoncia",
            duracion_min=60,
            precio_base=Decimal("45000.00"),
            sena_pct=30,
        )
    )
    await db_session.flush()

    repo = TipoPracticaRepository(db_session)
    practicas = await repo.list_activas(clinic_a.id)

    assert [p.nombre for p in practicas] == ["Limpieza"]


@pytest.mark.asyncio
async def test_repositorio_aranceles_filtra_por_clinic(db_session: AsyncSession):
    """ArancelRepository.list_by_clinic devuelve solo aranceles de la clínica."""
    clinic_a = await _crear_clinic(db_session, "Clínica Arancel Repo A")
    clinic_b = await _crear_clinic(db_session, "Clínica Arancel Repo B")
    tipo_a = TipoPractica(
        clinic_id=clinic_a.id,
        nombre="Limpieza",
        duracion_min=30,
        precio_base=Decimal("15000.00"),
        sena_pct=30,
    )
    tipo_b = TipoPractica(
        clinic_id=clinic_b.id,
        nombre="Endodoncia",
        duracion_min=60,
        precio_base=Decimal("45000.00"),
        sena_pct=30,
    )
    db_session.add_all([tipo_a, tipo_b])
    await db_session.flush()
    db_session.add_all(
        [
            Arancel(
                tipo_practica_id=tipo_a.id,
                precio=Decimal("15000.00"),
                sena_pct=30,
                vigente_desde=date(2026, 1, 1),
            ),
            Arancel(
                tipo_practica_id=tipo_b.id,
                precio=Decimal("45000.00"),
                sena_pct=30,
                vigente_desde=date(2026, 1, 1),
            ),
        ]
    )
    await db_session.flush()

    repo = ArancelRepository(db_session)
    aranceles = await repo.list_by_clinic(clinic_a.id)

    assert len(aranceles) == 1
    assert aranceles[0].tipo_practica_id == tipo_a.id
