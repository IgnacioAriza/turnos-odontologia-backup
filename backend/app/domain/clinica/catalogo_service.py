"""Servicio del catálogo clínico: resolución de precios y cambios auditados."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.clinica.models import Arancel, AuditoriaSena, TipoPractica
from app.domain.clinica.repository import TipoPracticaRepository


def precio_efectivo(tipo_practica: TipoPractica, arancel: Arancel | None, fecha: date) -> Decimal:
    """Resolver el precio efectivo de una práctica a una fecha.

    Precedencia (design D4): si existe un arancel con `vigente_desde` menor o
    igual a la fecha, se usa su precio; en caso contrario, el precio base de la
    práctica.
    """
    if arancel is not None and arancel.vigente_desde <= fecha:
        return arancel.precio
    return tipo_practica.precio_base


async def actualizar_sena_pct(
    session: AsyncSession,
    *,
    clinic_id: UUID,
    tipo_practica_id: UUID,
    nuevo_pct: int,
    usuario_id: UUID | None,
) -> TipoPractica | None:
    """Actualizar el % seña de una práctica y registrar la auditoría.

    Devuelve `None` cuando la práctica no existe o no pertenece a la clínica.
    El cambio y su registro de auditoría se confirman en la misma transacción.
    """
    if not 0 <= nuevo_pct <= 100:
        raise ValueError("sena_pct debe estar entre 0 y 100")

    repo = TipoPracticaRepository(session)
    tipo = await repo.get_by_clinic(clinic_id, tipo_practica_id)
    if tipo is None:
        return None

    valor_anterior = tipo.sena_pct
    tipo.sena_pct = nuevo_pct
    session.add(
        AuditoriaSena(
            clinic_id=clinic_id,
            tipo_practica_id=tipo.id,
            usuario_id=usuario_id,
            valor_anterior=valor_anterior,
            valor_nuevo=nuevo_pct,
        )
    )

    await session.flush()
    await session.commit()
    await session.refresh(tipo)
    return tipo
