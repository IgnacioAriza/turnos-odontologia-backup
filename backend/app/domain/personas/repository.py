"""Repositorios del dominio personas."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository, UnitOfWork
from app.domain.personas.models import Paciente, User


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, clinic_id: UUID, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(
                User.clinic_id == clinic_id,
                User.email == email,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_clinic(
        self,
        clinic_id: UUID,
        rol: str | None = None,
        is_active: bool | None = None,
    ) -> list[User]:
        query = select(User).where(User.clinic_id == clinic_id)
        if rol is not None:
            query = query.where(User.rol == rol)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_odontologos(self, clinic_id: UUID) -> list[User]:
        """Odontólogos activos de la clínica, ordenados por email."""
        result = await self.session.execute(
            select(User)
            .where(
                User.clinic_id == clinic_id,
                User.rol == "odonto",
                User.activo.is_(True),
                User.is_active.is_(True),
            )
            .order_by(User.email)
        )
        return list(result.scalars().all())


class PacienteRepository(BaseRepository[Paciente]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Paciente)

    async def get_by_dni(self, clinic_id: UUID, dni: str) -> Paciente | None:
        result = await self.session.execute(
            select(Paciente).where(
                Paciente.clinic_id == clinic_id,
                Paciente.dni == dni,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_telefono(self, clinic_id: UUID, telefono: str) -> Paciente | None:
        result = await self.session.execute(
            select(Paciente).where(
                Paciente.clinic_id == clinic_id,
                Paciente.telefono == telefono,
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_by_telefono(
        self,
        *,
        clinic_id: UUID,
        telefono: str,
        nombre: str,
        dni: str | None = None,
    ) -> Paciente:
        """Obtener o crear el paciente por `(clinic_id, telefono)`.

        La creación usa un savepoint para que una carrera con otro request que
        inserte el mismo teléfono no invalide la transacción completa: se captura
        `IntegrityError`, se hace rollback del savepoint y se re-selecciona.
        """
        existente = await self.get_by_telefono(clinic_id, telefono)
        if existente is not None:
            return existente

        try:
            async with self.session.begin_nested():
                paciente = Paciente(
                    clinic_id=clinic_id,
                    nombre=nombre,
                    telefono=telefono,
                    dni=dni,
                    is_active=True,
                )
                self.session.add(paciente)
                await self.session.flush()
            return paciente
        except IntegrityError:
            existente = await self.get_by_telefono(clinic_id, telefono)
            if existente is None:
                raise
            return existente


__all__ = ["UserRepository", "PacienteRepository", "UnitOfWork"]
