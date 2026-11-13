"""Repositorios del motor de turnos (C-05)."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.repository import BaseRepository
from app.domain.clinica.models import Sillon
from app.domain.turnos.models import ESTADOS_PANEL, ESTADOS_VIGENTES, HorarioAtencion, Turno


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

    async def list_agenda(
        self,
        clinic_id: UUID,
        *,
        desde: datetime,
        hasta: datetime,
        sillon_id: UUID | None = None,
        odontologo_id: UUID | None = None,
        estado: str | None = None,
    ) -> list[Turno]:
        """Turnos de la clínica en `[desde, hasta)` para la agenda operativa.

        Orden estable por `inicio`, nombre de sillón y `odontologo_id` (C-07
        D2). Los `cancelado` se excluyen salvo que se pidan explícitamente.
        Las relaciones se cargan con `selectinload` para no disparar IO perezoso
        al serializar la respuesta.
        """
        query = (
            select(Turno)
            .join(Turno.sillon)
            .options(
                selectinload(Turno.sillon),
                selectinload(Turno.paciente),
                selectinload(Turno.tipo_practica),
                selectinload(Turno.odontologo),
            )
            .where(
                Turno.clinic_id == clinic_id,
                Turno.inicio >= desde,
                Turno.inicio < hasta,
                Turno.is_active.is_(True),
            )
            .order_by(Turno.inicio, Sillon.nombre, Turno.odontologo_id)
        )
        if sillon_id is not None:
            query = query.where(Turno.sillon_id == sillon_id)
        if odontologo_id is not None:
            query = query.where(Turno.odontologo_id == odontologo_id)
        if estado is None:
            query = query.where(Turno.estado != "cancelado")
        else:
            query = query.where(Turno.estado == estado)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def list_panel_dia(
        self,
        clinic_id: UUID,
        *,
        desde: datetime,
        hasta: datetime,
        odontologo_id: UUID | None = None,
    ) -> list[Turno]:
        """Turnos operables del día para el panel, ordenados por hora (C-07)."""
        query = (
            select(Turno)
            .options(
                selectinload(Turno.sillon),
                selectinload(Turno.paciente),
                selectinload(Turno.tipo_practica),
                selectinload(Turno.odontologo),
            )
            .where(
                Turno.clinic_id == clinic_id,
                Turno.inicio >= desde,
                Turno.inicio < hasta,
                Turno.estado.in_(ESTADOS_PANEL),
                Turno.is_active.is_(True),
            )
            .order_by(Turno.inicio, Turno.sillon_id)
        )
        if odontologo_id is not None:
            query = query.where(Turno.odontologo_id == odontologo_id)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_panel_turno(self, clinic_id: UUID, turno_id: UUID) -> Turno | None:
        """Turno de la clínica con sus relaciones listo para el panel."""
        result = await self.session.execute(
            select(Turno)
            .options(
                selectinload(Turno.sillon),
                selectinload(Turno.paciente),
                selectinload(Turno.tipo_practica),
                selectinload(Turno.odontologo),
            )
            .where(
                Turno.id == turno_id,
                Turno.clinic_id == clinic_id,
                Turno.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

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
