"""Tests para los modelos del catálogo: TipoPractica, Arancel y AuditoriaSena."""

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clinica.models import Arancel, AuditoriaSena, Clinic, TipoPractica
from app.domain.personas import models as _personas_models  # noqa: F401


async def _crear_clinic(db_session: AsyncSession, nombre: str) -> Clinic:
    clinic = Clinic(nombre=nombre, timezone="America/Argentina/Buenos_Aires")
    db_session.add(clinic)
    await db_session.flush()
    return clinic


async def _crear_tipo(
    db_session: AsyncSession,
    clinic: Clinic,
    *,
    nombre: str = "Limpieza",
    duracion_min: int = 30,
    precio_base: Decimal = Decimal("15000.00"),
    sena_pct: int = 30,
) -> TipoPractica:
    tipo = TipoPractica(
        clinic_id=clinic.id,
        nombre=nombre,
        duracion_min=duracion_min,
        precio_base=precio_base,
        sena_pct=sena_pct,
    )
    db_session.add(tipo)
    await db_session.flush()
    return tipo


@pytest.mark.asyncio
async def test_tipo_practica_model(db_session: AsyncSession):
    """TipoPractica persiste sus campos y defaults de auditoría."""
    clinic = await _crear_clinic(db_session, "Clínica TipoPráctica")

    tipo = await _crear_tipo(db_session, clinic)

    assert tipo.id is not None
    assert tipo.clinic_id == clinic.id
    assert tipo.nombre == "Limpieza"
    assert tipo.duracion_min == 30
    assert tipo.precio_base == Decimal("15000.00")
    assert tipo.sena_pct == 30
    assert tipo.activa is True
    assert tipo.is_active is True
    assert tipo.created_at is not None
    assert tipo.updated_at is not None


@pytest.mark.asyncio
async def test_tipo_practica_unique_nombre_por_clinica(db_session: AsyncSession):
    """No se puede repetir el nombre de práctica dentro de la misma clínica."""
    clinic = await _crear_clinic(db_session, "Clínica UNIQUE")
    await _crear_tipo(db_session, clinic, nombre="Limpieza")

    db_session.add(
        TipoPractica(
            clinic_id=clinic.id,
            nombre="Limpieza",
            duracion_min=30,
            precio_base=Decimal("15000.00"),
            sena_pct=30,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_tipo_practica_mismo_nombre_en_otra_clinica(db_session: AsyncSession):
    """El mismo nombre puede existir en clínicas distintas."""
    clinic_a = await _crear_clinic(db_session, "Clínica A")
    clinic_b = await _crear_clinic(db_session, "Clínica B")

    tipo_a = await _crear_tipo(db_session, clinic_a, nombre="Limpieza")
    tipo_b = await _crear_tipo(db_session, clinic_b, nombre="Limpieza")

    assert tipo_a.id is not None
    assert tipo_b.id is not None


@pytest.mark.asyncio
async def test_tipo_practica_relacion_con_clinic(db_session: AsyncSession):
    """La relación Clinic -> TipoPractica queda navegable."""
    clinic = await _crear_clinic(db_session, "Clínica Relación")
    await _crear_tipo(db_session, clinic)

    result = await db_session.execute(select(Clinic).where(Clinic.id == clinic.id))
    clinic_cargada = result.scalar_one()
    await db_session.refresh(clinic_cargada, attribute_names=["tipos_practica"])
    tipos = clinic_cargada.tipos_practica

    assert len(tipos) == 1
    assert tipos[0].nombre == "Limpieza"


def test_tipo_practica_fk_a_clinic():
    """Kaliwatan FK de tipos_practica hacia clinic.id."""
    fks = list(TipoPractica.__table__.foreign_keys)
    destinos = {fk.target_fullname for fk in fks}

    assert "clinic.id" in destinos


@pytest.mark.asyncio
async def test_arancel_model(db_session: AsyncSession):
    """Arancel persiste precio, sena_pct y vigencia asociado a una práctica."""
    clinic = await _crear_clinic(db_session, "Clínica Arancel")
    tipo = await _crear_tipo(db_session, clinic)

    arancel = Arancel(
        tipo_practica_id=tipo.id,
        precio=Decimal("25000.00"),
        sena_pct=40,
        vigente_desde=date(2026, 1, 1),
    )
    db_session.add(arancel)
    await db_session.flush()

    assert arancel.id is not None
    assert arancel.tipo_practica_id == tipo.id
    assert arancel.precio == Decimal("25000.00")
    assert arancel.sena_pct == 40
    assert arancel.is_active is True


@pytest.mark.asyncio
async def test_arancel_unico_por_practica(db_session: AsyncSession):
    """Solo puede existir un arancel por práctica."""
    clinic = await _crear_clinic(db_session, "Clínica Arancel UNIQUE")
    tipo = await _crear_tipo(db_session, clinic)

    db_session.add(
        Arancel(
            tipo_practica_id=tipo.id,
            precio=Decimal("25000.00"),
            sena_pct=40,
            vigente_desde=date(2026, 1, 1),
        )
    )
    await db_session.flush()

    db_session.add(
        Arancel(
            tipo_practica_id=tipo.id,
            precio=Decimal("30000.00"),
            sena_pct=50,
            vigente_desde=date(2026, 6, 1),
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


def test_arancel_fk_a_tipo_practica():
    """Kaliwatan FK de aranceles hacia tipos_practica.id."""
    fks = list(Arancel.__table__.foreign_keys)
    destinos = {fk.target_fullname for fk in fks}

    assert "tipos_practica.id" in destinos


@pytest.mark.asyncio
async def test_auditoria_sena_model(db_session: AsyncSession):
    """AuditoriaSena registra valores anterior y nuevo del porcentaje."""
    clinic = await _crear_clinic(db_session, "Clínica Auditoría")
    tipo = await _crear_tipo(db_session, clinic)

    auditoria = AuditoriaSena(
        clinic_id=clinic.id,
        tipo_practica_id=tipo.id,
        usuario_id=uuid4(),
        valor_anterior=30,
        valor_nuevo=40,
    )
    db_session.add(auditoria)
    await db_session.flush()

    assert auditoria.id is not None
    assert auditoria.clinic_id == clinic.id
    assert auditoria.valor_anterior == 30
    assert auditoria.valor_nuevo == 40
    assert auditoria.created_at is not None
    assert isinstance(auditoria.created_at, datetime)


@pytest.mark.asyncio
async def test_duracion_min_cero_es_rechazada(db_session: AsyncSession):
    """CHECK duracion_min > 0."""
    clinic = await _crear_clinic(db_session, "Clínica Duración")

    db_session.add(
        TipoPractica(
            clinic_id=clinic.id,
            nombre="Práctica inválida",
            duracion_min=0,
            precio_base=Decimal("1000.00"),
            sena_pct=10,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_sena_pct_negativa_es_rechazada(db_session: AsyncSession):
    """CHECK sena_pct >= 0."""
    clinic = await _crear_clinic(db_session, "Clínica Seña negativa")

    db_session.add(
        TipoPractica(
            clinic_id=clinic.id,
            nombre="Práctica inválida",
            duracion_min=30,
            precio_base=Decimal("1000.00"),
            sena_pct=-1,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_sena_pct_mayor_a_cien_es_rechazada(db_session: AsyncSession):
    """CHECK sena_pct <= 100."""
    clinic = await _crear_clinic(db_session, "Clínica Seña alta")

    db_session.add(
        TipoPractica(
            clinic_id=clinic.id,
            nombre="Práctica inválida",
            duracion_min=30,
            precio_base=Decimal("1000.00"),
            sena_pct=101,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_sena_pct_limites_aceptados(db_session: AsyncSession):
    """Los extremos 0 y 100 son válidos."""
    clinic = await _crear_clinic(db_session, "Clínica Límites")

    tipo_cero = await _crear_tipo(db_session, clinic, nombre="Sin seña", sena_pct=0)
    tipo_cien = await _crear_tipo(db_session, clinic, nombre="Seña total", sena_pct=100)

    assert tipo_cero.sena_pct == 0
    assert tipo_cien.sena_pct == 100


@pytest.mark.asyncio
async def test_precio_base_negativo_es_rechazado(db_session: AsyncSession):
    """CHECK precio_base >= 0."""
    clinic = await _crear_clinic(db_session, "Clínica Precio negativo")

    db_session.add(
        TipoPractica(
            clinic_id=clinic.id,
            nombre="Práctica inválida",
            duracion_min=30,
            precio_base=Decimal("-1.00"),
            sena_pct=10,
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_precio_arancel_negativo_es_rechazado(db_session: AsyncSession):
    """CHECK precio >= 0 en aranceles."""
    clinic = await _crear_clinic(db_session, "Clínica Arancel negativo")
    tipo = await _crear_tipo(db_session, clinic)

    db_session.add(
        Arancel(
            tipo_practica_id=tipo.id,
            precio=Decimal("-1.00"),
            sena_pct=10,
            vigente_desde=datetime.now(UTC),
        )
    )

    with pytest.raises(IntegrityError):
        await db_session.flush()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_aislamiento_por_clinic_id(db_session: AsyncSession):
    """Una consulta filtrada por clinic_id no devuelve prácticas de otra clínica."""
    clinic_a = await _crear_clinic(db_session, "Clínica Aislamiento A")
    clinic_b = await _crear_clinic(db_session, "Clínica Aislamiento B")
    await _crear_tipo(db_session, clinic_a, nombre="Limpieza")
    await _crear_tipo(db_session, clinic_b, nombre="Endodoncia")

    result = await db_session.execute(
        select(TipoPractica).where(TipoPractica.clinic_id == clinic_a.id)
    )
    tipos = list(result.scalars().all())

    assert len(tipos) == 1
    assert tipos[0].nombre == "Limpieza"
