"""Repositorios del dominio personas."""

from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository, UnitOfWork
from app.domain.personas.models import User, Paciente


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, clinic_id: UUID, email: str) -> Optional[User]:
        result = await self.session.execute(
            select(User).where(
                User.clinic_id == clinic_id,  # type: ignore[attr-defined]
                User.email == email,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_clinic(
        self,
        clinic_id: UUID,
        rol: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[User]:
        from sqlalchemy import select as sa_select
        query = sa_select(User).where(User.clinic_id == clinic_id)  # type: ignore[attr-defined]
        if rol is not None:
            query = query.where(User.rol == rol)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        result = await self.session.execute(query)
        return result.scalars().all()


class PacienteRepository(BaseRepository[Paciente]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Paciente)

    async def get_by_dni(self, clinic_id: UUID, dni: str) -> Optional[Paciente]:
        result = await self.session.execute(
            select(Paciente).where(
                Paciente.clinic_id == clinic_id,  # type: ignore[attr-defined]
                Paciente.dni == dni,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_telefono(
        self, clinic_id: UUID, telefono: str
    ) -> Optional[Paciente]:
        result = await self.session.execute(
            select(Paciente).where(
                Paciente.clinic_id == clinic_id,  # type: ignore[attr-defined]
                Paciente.telefono == telefono,
            )
        )
        return result.scalar_one_or_none()


__all__ = ["UserRepository", "PacienteRepository", "UnitOfWork"]
