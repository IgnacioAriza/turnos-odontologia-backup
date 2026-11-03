"""BaseRepository genérico y UnitOfWork para el dominio de turnos-odontologia.

Sigue el patrón Repository + Unit of Work para desacoplar la lógica de negocio
de la persistencia y gestionar límites de transacción explícitos.
"""

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Repositorio genérico con operaciones CRUD sobre un modelo SQLAlchemy."""

    def __init__(self, session: AsyncSession, model: type[ModelType]):
        self.session = session
        self.model = model

    async def get(self, id: UUID | int) -> ModelType | None:
        """Obtener un registro por su ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        clinic_id: UUID | int | None = None,
        is_active: bool | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ModelType]:
        """Listar registros con filtros opcionales de clinic_id e is_active."""
        query = select(self.model)

        if clinic_id is not None and hasattr(self.model, "clinic_id"):
            query = query.where(self.model.clinic_id == clinic_id)  # type: ignore[attr-defined]

        if is_active is not None and hasattr(self.model, "is_active"):
            query = query.where(self.model.is_active == is_active)  # type: ignore[attr-defined]

        query = query.offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def create(self, obj_in: dict[str, Any]) -> ModelType:
        """Crear un nuevo registro."""
        db_obj = self.model(**obj_in)
        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def update(
        self,
        id: UUID | int,
        obj_in: dict[str, Any],
    ) -> ModelType | None:
        """Actualizar un registro existente por su ID."""
        db_obj = await self.get(id)
        if db_obj is None:
            return None

        for field, value in obj_in.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)

        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, id: UUID | int) -> bool:
        """Eliminar (soft delete) un registro por su ID."""
        db_obj = await self.get(id)
        if db_obj is None:
            return False

        if hasattr(db_obj, "is_active"):
            db_obj.is_active = False
            await self.session.flush()
        else:
            await self.session.delete(db_obj)
            await self.session.flush()

        return True


class UnitOfWork:
    """Unit of Work que gestiona los límites de transacción.

    Proporciona commit() y rollback() para agrupar múltiples operaciones
    de repositorio en una sola transacción atómica.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def commit(self) -> None:
        """Confirmar la transacción actual."""
        await self.session.commit()

    async def rollback(self) -> None:
        """Deshacer la transacción actual."""
        await self.session.rollback()
