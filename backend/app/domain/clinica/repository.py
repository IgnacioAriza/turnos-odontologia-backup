"""Repositorios del dominio clínica."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository, UnitOfWork
from app.domain.clinica.models import Arancel, AuditoriaSena, Bloqueo, Clinic, Sillon, TipoPractica


class ClinicRepository(BaseRepository[Clinic]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Clinic)

    async def get_by_nombre(self, clinic_id: UUID, nombre: str) -> Clinic | None:
        result = await self.session.execute(
            select(Clinic).where(Clinic.id == clinic_id, Clinic.nombre == nombre)
        )
        return result.scalar_one_or_none()


class SillonRepository(BaseRepository[Sillon]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Sillon)

    async def get_by_clinic(self, clinic_id: UUID, activo: bool | None = None) -> list[Sillon]:
        return await self.list(clinic_id=clinic_id, is_active=activo)

    async def list_activos(self, clinic_id: UUID) -> list[Sillon]:
        result = await self.session.execute(
            select(Sillon)
            .where(
                Sillon.clinic_id == clinic_id, Sillon.activo.is_(True), Sillon.is_active.is_(True)
            )
            .order_by(Sillon.nombre)
        )
        return list(result.scalars().all())


class BloqueoRepository(BaseRepository[Bloqueo]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Bloqueo)

    async def get_by_clinic(self, clinic_id: UUID, is_active: bool | None = None) -> list[Bloqueo]:
        return await self.list(clinic_id=clinic_id, is_active=is_active)

    async def get_by_paciente(
        self, paciente_id: UUID, is_active: bool | None = None
    ) -> list[Bloqueo]:
        query = select(Bloqueo).where(Bloqueo.paciente_id == paciente_id)
        if is_active is not None:
            query = query.where(Bloqueo.is_active == is_active)
        result = await self.session.execute(query)
        return list(result.scalars().all())


class TipoPracticaRepository(BaseRepository[TipoPractica]):
    """Repositorio de prácticas del catálogo."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, TipoPractica)

    async def list_activas(self, clinic_id: UUID) -> list[TipoPractica]:
        result = await self.session.execute(
            select(TipoPractica)
            .where(
                TipoPractica.clinic_id == clinic_id,
                TipoPractica.activa.is_(True),
                TipoPractica.is_active.is_(True),
            )
            .order_by(TipoPractica.nombre)
        )
        return list(result.scalars().all())

    async def list_by_clinic(self, clinic_id: UUID) -> list[TipoPractica]:
        result = await self.session.execute(
            select(TipoPractica)
            .where(TipoPractica.clinic_id == clinic_id, TipoPractica.is_active.is_(True))
            .order_by(TipoPractica.nombre)
        )
        return list(result.scalars().all())

    async def list_activas_publicas(self) -> list[TipoPractica]:
        """Prácticas reservables del despliegue, sin filtrar por clínica.

        El canal público no tiene contexto de clínica: la instalación es de una
        sola clínica (KB 01/02). Si el producto se vuelve multi-clínica, este
        método debe recibir el tenant resuelto por dominio o subdominio.
        """
        result = await self.session.execute(
            select(TipoPractica)
            .where(TipoPractica.activa.is_(True), TipoPractica.is_active.is_(True))
            .order_by(TipoPractica.nombre)
        )
        return list(result.scalars().all())

    async def get_by_clinic(self, clinic_id: UUID, tipo_practica_id: UUID) -> TipoPractica | None:
        result = await self.session.execute(
            select(TipoPractica).where(
                TipoPractica.id == tipo_practica_id, TipoPractica.clinic_id == clinic_id
            )
        )
        return result.scalar_one_or_none()


class ArancelRepository(BaseRepository[Arancel]):
    """Repositorio de aranceles por práctica."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Arancel)

    async def get_by_tipo(self, tipo_practica_id: UUID) -> Arancel | None:
        result = await self.session.execute(
            select(Arancel).where(Arancel.tipo_practica_id == tipo_practica_id)
        )
        return result.scalar_one_or_none()

    async def list_by_clinic(self, clinic_id: UUID) -> list[Arancel]:
        result = await self.session.execute(
            select(Arancel)
            .join(TipoPractica, Arancel.tipo_practica_id == TipoPractica.id)
            .where(TipoPractica.clinic_id == clinic_id, Arancel.is_active.is_(True))
            .order_by(TipoPractica.nombre)
        )
        return list(result.scalars().all())


class AuditoriaSenaRepository(BaseRepository[AuditoriaSena]):
    """Repositorio append-only de auditoría de cambios de seña."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, AuditoriaSena)

    async def list_by_tipo(self, clinic_id: UUID, tipo_practica_id: UUID) -> list[AuditoriaSena]:
        result = await self.session.execute(
            select(AuditoriaSena)
            .where(
                AuditoriaSena.clinic_id == clinic_id,
                AuditoriaSena.tipo_practica_id == tipo_practica_id,
            )
            .order_by(AuditoriaSena.created_at)
        )
        return list(result.scalars().all())


__all__ = [
    "ClinicRepository",
    "SillonRepository",
    "BloqueoRepository",
    "TipoPracticaRepository",
    "ArancelRepository",
    "AuditoriaSenaRepository",
    "UnitOfWork",
]
