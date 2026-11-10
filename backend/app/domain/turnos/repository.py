"""Repositorios del motor de turnos (C-05)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.repository import BaseRepository
from app.domain.turnos.models import ESTADOS_VIGENTES, HorarioAtencion, Turno


class HorarioAtencionRepository(BaseRepository[HorarioAtencion]):
    """Franjas de atención por clínica y día de semana."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, HorarioAtencion)

    async def list_by_clinic(self, clinic_id: UUID) -> list[HorarioAtencion]:
        result = await self.session.execute(
            select(HorarioAtencion)
            .where(
                HorarioAtencion.clinic_id == clinic_id,
                HorarioAtencion.activo.is_(True),
                HorarioAtencion.is_active.is_(True),
            )
            .order_by(HorarioAtencion.dia_semana, HorarioAtencion.hora_desde)
        )
        return list(result.scalars().all())

    async def list_by_dia(self, clinic_id: UUID, dia_semana: int) -> list[HorarioAtencion]:
        result = await self.session.execute(
            select(HorarioAtencion)
            .where(
                HorarioAtencion.clinic_id == clinic_id,
                HorarioAtencion.dia_semana == dia_semana,
                HorarioAtencion.activo.is_(True),
                HorarioAtencion.is_active.is_(True),
            )
            .order_by(HorarioAtencion.hora_desde)
        )
        return list(result.scalars().all())


class TurnoRepository(BaseRepository[Turno]):
    """Turnos de la clínica con consultas de solape y token público."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, Turno)

    async def get_by_manage_token(self, manage_token: str) -> Turno | None:
        result = await self.session.execute(select(Turno).where(Turno.manage_token == manage_token))
        return result.scalar_one_or_none()

    async def list_vigentes_en_rango(
        self, clinic_id: UUID, inicio: datetime, fin: datetime
    ) -> list[Turno]:
        """Turnos vigentes que se superponen con el rango pedido."""
        result = await self.session.execute(
            select(Turno).where(
                Turno.clinic_id == clinic_id,
                Turno.estado.in_(ESTADOS_VIGENTES),
                Turno.inicio < fin,
                Turno.fin > inicio,
            )
        )
        return list(result.scalars().all())

    async def list_por_practica_en_rango(
        self, tipo_practica_id: UUID, inicio: datetime, fin: datetime
    ) -> list[Turno]:
        result = await self.session.execute(
            select(Turno).where(
                Turno.tipo_practica_id == tipo_practica_id,
                Turno.inicio < fin,
                Turno.fin > inicio,
            )
        )
        return list(result.scalars().all())

    async def get_solape_sillon(
        self, sillon_id: UUID, inicio: datetime, fin: datetime
    ) -> Turno | None:
        result = await self.session.execute(
            select(Turno)
            .where(
                Turno.sillon_id == sillon_id,
                Turno.estado.in_(ESTADOS_VIGENTES),
                Turno.inicio < fin,
                Turno.fin > inicio,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_solape_odontologo(
        self, odontologo_id: UUID, inicio: datetime, fin: datetime
    ) -> Turno | None:
        result = await self.session.execute(
            select(Turno)
            .where(
                Turno.odontologo_id == odontologo_id,
                Turno.estado.in_(ESTADOS_VIGENTES),
                Turno.inicio < fin,
                Turno.fin > inicio,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()


__all__ = ["HorarioAtencionRepository", "TurnoRepository"]
