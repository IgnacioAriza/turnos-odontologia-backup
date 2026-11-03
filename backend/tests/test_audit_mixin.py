"""Tests para AuditMixin (is_active, created_at, updated_at)."""

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clinica.models import Clinic, Sillon


@pytest.mark.asyncio
async def test_audit_mixin_fields(db_session: AsyncSession):
    """Todos los modelos de negocio deben tener is_active, created_at, updated_at."""
    clinic = Clinic(
        nombre="Audit Test Clinic",
        timezone="America/Argentina/Buenos_Aires",
    )
    db_session.add(clinic)
    await db_session.flush()

    assert clinic.is_active is True
    assert isinstance(clinic.created_at, datetime)
    assert isinstance(clinic.updated_at, datetime)

    sillon = Sillon(
        clinic_id=clinic.id,
        nombre="Sillón Audit",
    )
    db_session.add(sillon)
    await db_session.flush()

    assert sillon.is_active is True
    assert isinstance(sillon.created_at, datetime)
    assert isinstance(sillon.updated_at, datetime)


@pytest.mark.asyncio
async def test_clinic_inherits_audit_mixin(db_session: AsyncSession):
    """Clinic también hereda AuditMixin (aunque no tenga clinic_id)."""
    clinic = Clinic(
        nombre="Clinic Audit Test",
        timezone="America/Argentina/Buenos_Aires",
    )
    db_session.add(clinic)
    await db_session.flush()

    assert hasattr(clinic, "is_active")
    assert hasattr(clinic, "created_at")
    assert hasattr(clinic, "updated_at")
