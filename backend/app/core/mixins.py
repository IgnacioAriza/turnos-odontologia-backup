"""AuditMixin para modelos de negocio.

Proporciona campos de auditoría comunes: is_active, created_at, updated_at.
Permite soft deletes y trazabilidad de creación/actualización.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class AuditMixin:
    """Mixin de auditoría para modelos de negocio.

    Todos los modelos de negocio (excepto Clinic) deben heredar de este mixin
    para tener campos de auditoría consistentes.
    """

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
