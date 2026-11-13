"""Modelos del dominio clínica: Clinic, Sillon, Bloqueo, TipoPractica, Arancel."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.mixins import AuditMixin
from app.infrastructure.db.base import Base

if TYPE_CHECKING:
    from app.domain.personas.models import Paciente, User
    from app.domain.turnos.models import Turno


class Clinic(Base, AuditMixin):
    """Clínica odontológica. Una sola en v1 (sin multi-sede, pero clinic_id desde día 1)."""

    __tablename__ = "clinic"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    timezone: Mapped[str] = mapped_column(
        String(64), default="America/Argentina/Buenos_Aires", nullable=False
    )
    wa_sender: Mapped[str | None] = mapped_column(String(50), nullable=True)
    mp_account: Mapped[str | None] = mapped_column(String(200), nullable=True)

    # Relaciones
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="clinic", cascade="all, delete-orphan"
    )
    pacientes: Mapped[list["Paciente"]] = relationship(
        "Paciente", back_populates="clinic", cascade="all, delete-orphan"
    )
    sillones: Mapped[list["Sillon"]] = relationship(
        "Sillon", back_populates="clinic", cascade="all, delete-orphan"
    )
    bloqueos: Mapped[list["Bloqueo"]] = relationship(
        "Bloqueo", back_populates="clinic", cascade="all, delete-orphan"
    )
    tipos_practica: Mapped[list["TipoPractica"]] = relationship(
        "TipoPractica", back_populates="clinic", cascade="all, delete-orphan"
    )


class Sillon(Base, AuditMixin):
    """Sillón odontológico de la clínica."""

    __tablename__ = "sillones"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    clinic_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinic.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)

    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="sillones")


class Bloqueo(Base, AuditMixin):
    """Bloqueo de paciente (por ausentismo, 30 días). Lógica completa en C-07."""

    __tablename__ = "bloqueos"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    clinic_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinic.id", ondelete="CASCADE"), nullable=False, index=True
    )
    paciente_id: Mapped[UUID] = mapped_column(
        ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    desde: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hasta: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str | None] = mapped_column(String(200), nullable=True)

    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="bloqueos")
    paciente: Mapped["Paciente"] = relationship("Paciente", back_populates="bloqueos")


class ExcepcionBloqueo(Base, AuditMixin):
    """Excepción auditada al bloqueo por ausentismo (C-07, RN-AUS-02).

    Una fila por turno creado con `motivo_excepcion`: expresa quién autorizó
    reservar a un paciente bloqueado y por qué. `UNIQUE(turno_id)` evita
    duplicados si el alta se reintenta.
    """

    __tablename__ = "excepciones_bloqueo"
    __table_args__ = (
        UniqueConstraint("turno_id", name="uq_excepciones_bloqueo_turno_id"),
        Index("ix_excepciones_bloqueo_clinic_created", "clinic_id", "created_at"),
        Index("ix_excepciones_bloqueo_paciente", "paciente_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    clinic_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinic.id", ondelete="CASCADE"), nullable=False
    )
    paciente_id: Mapped[UUID] = mapped_column(
        ForeignKey("pacientes.id", ondelete="CASCADE"), nullable=False
    )
    turno_id: Mapped[UUID] = mapped_column(
        ForeignKey("turnos.id", ondelete="CASCADE"), nullable=False
    )
    usuario_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    motivo: Mapped[str] = mapped_column(Text, nullable=False)

    clinic: Mapped["Clinic"] = relationship("Clinic")
    paciente: Mapped["Paciente"] = relationship("Paciente")
    turno: Mapped["Turno"] = relationship("Turno")
    usuario: Mapped["User"] = relationship("User")


class TipoPractica(Base, AuditMixin):
    """Práctica odontológica del catálogo clínico (C-04)."""

    __tablename__ = "tipos_practica"
    __table_args__ = (
        CheckConstraint("duracion_min > 0", name="ck_tipos_practica_duracion_min_positiva"),
        CheckConstraint("precio_base >= 0", name="ck_tipos_practica_precio_base_no_negativo"),
        CheckConstraint(
            "sena_pct >= 0 AND sena_pct <= 100", name="ck_tipos_practica_sena_pct_rango"
        ),
        UniqueConstraint("clinic_id", "nombre", name="uq_tipos_practica_clinic_id_nombre"),
        Index("ix_tipos_practica_clinic_id_activa", "clinic_id", "activa"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    clinic_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinic.id", ondelete="CASCADE"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    duracion_min: Mapped[int] = mapped_column(Integer, nullable=False)
    precio_base: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sena_pct: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activa: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="tipos_practica")
    arancel: Mapped["Arancel | None"] = relationship(
        "Arancel", back_populates="tipo_practica", uselist=False, cascade="all, delete-orphan"
    )
    auditorias_sena: Mapped[list["AuditoriaSena"]] = relationship(
        "AuditoriaSena", back_populates="tipo_practica", cascade="all, delete-orphan"
    )


class Arancel(Base, AuditMixin):
    """Arancel vigente de una práctica. Lectura en v1.0, CRUD en C-13."""

    __tablename__ = "aranceles"
    __table_args__ = (
        UniqueConstraint("tipo_practica_id", name="uq_aranceles_tipo_practica_id"),
        CheckConstraint("precio >= 0", name="ck_aranceles_precio_no_negativo"),
        CheckConstraint("sena_pct >= 0 AND sena_pct <= 100", name="ck_aranceles_sena_pct_rango"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tipo_practica_id: Mapped[UUID] = mapped_column(
        ForeignKey("tipos_practica.id", ondelete="CASCADE"), nullable=False, index=True
    )
    precio: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    sena_pct: Mapped[int] = mapped_column(Integer, nullable=False)
    vigente_desde: Mapped[date] = mapped_column(Date, nullable=False)

    tipo_practica: Mapped["TipoPractica"] = relationship("TipoPractica", back_populates="arancel")


class AuditoriaSena(Base, AuditMixin):
    """Registro append-only de cambios de % seña (RN-ADMIN-01)."""

    __tablename__ = "auditorias_sena"
    __table_args__ = (
        Index(
            "ix_auditorias_sena_clinic_tipo_created", "clinic_id", "tipo_practica_id", "created_at"
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    clinic_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinic.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tipo_practica_id: Mapped[UUID] = mapped_column(
        ForeignKey("tipos_practica.id", ondelete="CASCADE"), nullable=False, index=True
    )
    usuario_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    valor_anterior: Mapped[int] = mapped_column(Integer, nullable=False)
    valor_nuevo: Mapped[int] = mapped_column(Integer, nullable=False)

    tipo_practica: Mapped["TipoPractica"] = relationship(
        "TipoPractica", back_populates="auditorias_sena"
    )
