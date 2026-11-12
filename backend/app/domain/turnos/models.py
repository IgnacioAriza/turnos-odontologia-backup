"""Modelos del motor de turnos: Turno y HorarioAtencion (C-05)."""

from datetime import datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.mixins import AuditMixin
from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.domain.clinica.models import Clinic, Sillon, TipoPractica
    from app.domain.personas.models import Paciente, User

ESTADOS_TURNO = (
    "pendiente_sena",
    "confirmado",
    "cancelado",
    "reprogramado",
    "completado",
    "ausente",
)
ESTADOS_VIGENTES = ("pendiente_sena", "confirmado", "reprogramado")

_ESTADOS_SQL = ", ".join(f"'{estado}'" for estado in ESTADOS_TURNO)
_VIGENTES_SQL = ", ".join(f"'{estado}'" for estado in ESTADOS_VIGENTES)


class HorarioAtencion(Base, AuditMixin):
    """Franja de atención semanal de una clínica (0=lunes … 6=domingo)."""

    __tablename__ = "horarios_atencion"
    __table_args__ = (
        UniqueConstraint(
            "clinic_id",
            "dia_semana",
            "hora_desde",
            name="uq_horarios_atencion_clinic_dia_hora",
        ),
        CheckConstraint("dia_semana >= 0 AND dia_semana <= 6", name="ck_horarios_dia_semana_rango"),
        CheckConstraint("hora_hasta > hora_desde", name="ck_horarios_hora_hasta_mayor"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    clinic_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinic.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dia_semana: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    hora_desde: Mapped[time] = mapped_column(Time, nullable=False)
    hora_hasta: Mapped[time] = mapped_column(Time, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    clinic: Mapped["Clinic"] = relationship("Clinic")


class Turno(Base, AuditMixin):
    """Turno reservado para un paciente en un sillón con un odontólogo."""

    __tablename__ = "turnos"
    __table_args__ = (
        CheckConstraint("fin > inicio", name="ck_turnos_fin_mayor_inicio"),
        CheckConstraint("monto_sena >= 0", name="ck_turnos_monto_sena_no_negativo"),
        CheckConstraint(f"estado IN ({_ESTADOS_SQL})", name="ck_turnos_estado_valido"),
        UniqueConstraint("manage_token", name="uq_turnos_manage_token"),
        Index("ix_turnos_clinic_inicio", "clinic_id", "inicio"),
        Index("ix_turnos_sillon_inicio", "sillon_id", "inicio"),
        Index("ix_turnos_odontologo_inicio", "odontologo_id", "inicio"),
        Index("ix_turnos_paciente_inicio", "paciente_id", "inicio"),
        Index("ix_turnos_estado", "estado"),
        Index("ix_turnos_estado_expira", "estado", "expira_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    clinic_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinic.id", ondelete="CASCADE"), nullable=False, index=True
    )
    paciente_id: Mapped[UUID] = mapped_column(
        ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sillon_id: Mapped[UUID] = mapped_column(
        ForeignKey("sillones.id", ondelete="CASCADE"), nullable=False, index=True
    )
    odontologo_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo_practica_id: Mapped[UUID] = mapped_column(
        ForeignKey("tipos_practica.id", ondelete="CASCADE"), nullable=False, index=True
    )
    inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estado: Mapped[str] = mapped_column(String(32), default="pendiente_sena", nullable=False)
    manage_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    reprogramaciones_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monto_sena: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    expira_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # C-06: gestión por token. `sena_perdida` marca la seña retenida por cancelar
    # o reprogramar fuera de la ventana; `reprogramado_de_id` encadena las
    # reprogramaciones que exigen una nueva seña.
    sena_perdida: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reprogramado_de_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("turnos.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    clinic: Mapped["Clinic"] = relationship("Clinic")
    paciente: Mapped["Paciente"] = relationship("Paciente", back_populates="turnos")
    sillon: Mapped["Sillon"] = relationship("Sillon")
    odontologo: Mapped["User"] = relationship("User")
    tipo_practica: Mapped["TipoPractica"] = relationship("TipoPractica")
    reprogramado_de: Mapped["Turno | None"] = relationship(
        "Turno",
        remote_side="Turno.id",
        foreign_keys=[reprogramado_de_id],
    )
