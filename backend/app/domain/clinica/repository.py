"""Repositorios del dominio clínica."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository, UnitOfWork
from app.domain.clinica.models import Bloqueo, Clinic, Sillon


class ClinicRepository(BaseRepository[Clinic]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Clinic)

    async def get_by_nombre(self, clinic_id: UUID, nombre: str) -> Clinic | None:
        result = await self.session.execute(
            select(Clinic).where(
                Clinic.id == clinic_id,
                Clinic.nombre == nombre,
            )
        )
        return result.scalar_one_or_none()


class SillonRepository(BaseRepository[Sillon]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Sillon)

    async def get_by_clinic(
        self,
        clinic_id: UUID,
        activo: bool | None = None,
    ) -> list[Sillon]:
        return await self.list(clinic_id=clinic_id, is_active=activo)


class BloqueoRepository(BaseRepository[Bloqueo]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Bloqueo)

    async def get_by_clinic(
        self,
        clinic_id: UUID,
        is_active: bool | None = None,
    ) -> list[Bloqueo]:
        return await self.list(clinic_id=clinic_id, is_active=is_active)

    async def get_by_paciente(
        self,
        paciente_id: UUID,
        is_active: bool | None = None,
    ) -> list[Bloqueo]:
        query = select(Bloqueo).where(Bloqueo.paciente_id == paciente_id)
        if is_active is not None:
            query = query.where(Bloqueo.is_active == is_active)
        result = await self.session.execute(query)
        return list(result.scalars().all())


__all__ = ["ClinicRepository", "SillonRepository", "BloqueoRepository", "UnitOfWork"]
