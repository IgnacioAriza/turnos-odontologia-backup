"""Tests para BaseRepository y UnitOfWork."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import UnitOfWork
from app.domain.clinica.repository import ClinicRepository, SillonRepository


@pytest.mark.asyncio
async def test_repository_create_get(db_session: AsyncSession):
    repo = ClinicRepository(db_session)
    clinic = await repo.create(
        {
            "id": uuid4(),
            "nombre": "Repo Test Clinic",
            "timezone": "America/Argentina/Buenos_Aires",
        }
    )

    assert clinic.id is not None
    assert clinic.nombre == "Repo Test Clinic"

    fetched = await repo.get(clinic.id)
    assert fetched is not None
    assert fetched.nombre == "Repo Test Clinic"


@pytest.mark.asyncio
async def test_repository_list_by_clinic(db_session: AsyncSession):
    repo = ClinicRepository(db_session)
    clinic = await repo.create(
        {
            "id": uuid4(),
            "nombre": "List Test Clinic",
            "timezone": "America/Argentina/Buenos_Aires",
        }
    )

    sillon_repo = SillonRepository(db_session)
    await sillon_repo.create(
        {
            "id": uuid4(),
            "clinic_id": clinic.id,
            "nombre": "Sillón 1",
        }
    )
    await sillon_repo.create(
        {
            "id": uuid4(),
            "clinic_id": clinic.id,
            "nombre": "Sillón 2",
        }
    )

    sillones = await sillon_repo.get_by_clinic(clinic.id)
    assert len(sillones) == 2


@pytest.mark.asyncio
async def test_repository_update(db_session: AsyncSession):
    repo = ClinicRepository(db_session)
    clinic = await repo.create(
        {
            "id": uuid4(),
            "nombre": "Original Name",
            "timezone": "America/Argentina/Buenos_Aires",
        }
    )

    updated = await repo.update(clinic.id, {"nombre": "Updated Name"})
    assert updated is not None
    assert updated.nombre == "Updated Name"


@pytest.mark.asyncio
async def test_repository_delete_soft(db_session: AsyncSession):
    """Soft delete: is_active = False en lugar de eliminar físicamente."""
    repo = ClinicRepository(db_session)
    clinic = await repo.create(
        {
            "id": uuid4(),
            "nombre": "Delete Test",
            "timezone": "America/Argentina/Buenos_Aires",
        }
    )

    result = await repo.delete(clinic.id)
    assert result is True

    fetched = await repo.get(clinic.id)
    assert fetched is not None
    assert fetched.is_active is False


@pytest.mark.asyncio
async def test_unit_of_work_commit(db_session: AsyncSession):
    """UnitOfWork debe permitir commit."""
    uow = UnitOfWork(db_session)
    repo = ClinicRepository(db_session)

    await repo.create(
        {
            "id": uuid4(),
            "nombre": "UoW Test",
            "timezone": "America/Argentina/Buenos_Aires",
        }
    )

    await uow.commit()


@pytest.mark.asyncio
async def test_repository_get_nonexistent(db_session: AsyncSession):
    repo = ClinicRepository(db_session)
    result = await repo.get(uuid4())
    assert result is None
