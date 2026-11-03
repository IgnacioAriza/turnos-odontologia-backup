"""Modelos del dominio personas: User, Paciente."""

from uuid import UUID, uuid4
from sqlalchemy import String, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.base import Base
from app.core.mixins import AuditMixin


class User(Base, AuditMixin):
    """Usuario interno de la clínica (recepción, odontólogo, admin)."""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    clinic_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinic.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    rol: Mapped[str] = mapped_column(String(32), nullable=False)  # recepcion|odonto|admin
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)
    odontologo_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="users")  # noqa: F821
    odontologo: Mapped["User | None"] = relationship(  # noqa: F821
        "User", remote_side=[id], back_populates="pacientes_asignados"
    )
    pacientes_asignados: Mapped[list["User"]] = relationship(  # noqa: F821
        "User", remote_side=[odontologo_id], back_populates="odontologo"
    )


class Paciente(Base, AuditMixin):
    """Paciente de la clínica."""

    __tablename__ = "pacientes"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    clinic_id: Mapped[UUID] = mapped_column(
        ForeignKey("clinic.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    telefono: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    dni: Mapped[str] = mapped_column(String(20), nullable=False, index=True)

    clinic: Mapped["Clinic"] = relationship("Clinic", back_populates="pacientes")  # noqa: F821
    bloqueos: Mapped[list["Bloqueo"]] = relationship(  # noqa: F821
        "Bloqueo", back_populates="paciente", cascade="all, delete-orphan"
    )
