"""Modelos del dominio clínica: Clinic, Sillon, Bloqueo."""

from uuid import UUID, uuid4
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.core.mixins import AuditMixin


class Clinic(Base, AuditMixin):
    """Clínica odontológica. Una sola en v1 (sin multi-sede, pero clinic_id desde día 1)."""

    __tablename__ = "clinic"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64),
        default="America/Argentina/Buenos_Aires",
        nullable=False,
    )
    wa_sender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mp_account: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relaciones
    users: Mapped[list["User"]] = relationship(  # noqa: F821
        "User", back_populates="clinic", cascade="all, delete-orphan"
    )
    pacientes: Mapped[list["Paciente"]] = relationship(  # noqa: F821
        "Paciente", back_populates="clinic", cascade="all, delete-orphan"
    )
    sillones: Mapped[list["Sillon"]] = relationship(  # noqa: F821
        "Sillon", back_populates="clinic", cascade="all, delete-orphan"
    )
    bloqueos: Mapped[list["Bloqueo"]] = relationship(  # noqa: F821
        "Bloqueo", back_populates="clinic", cascade="all, delete-orphan"
    )


class Sillon(Base, AuditMixin):
    """Sillón odontológico de la clínica."""

    __tablename__ = "sillones"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    clinic_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinic.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)

    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="sillones")  # noqa: F821


class Bloqueo(Base, AuditMixin):
    """Bloqueo de paciente (por ausentismo, 30 días). Lógica completa en C-07."""

    __tablename__ = "bloqueos"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    clinic_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinic.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    paciente_id: Mapped[UUID] = mapped_column(
        ForeignKey("pacientes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    desde: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hasta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(200), nullable=True)

    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="bloqueos")  # noqa: F821
    paciente: Mapped["Paciente"] = relationship("Paciente", back_populates="bloqueos")  # noqa: F821
