"""Migración 002: esquema inicial de clínica y personas (C-02).

Crea las tablas: clinic, users, pacientes, sillones, bloqueos.
Incluye constraint UNIQUE (clinic_id, email) en users e índices compuestos
(clinic_id, telefono) y (clinic_id, dni) en pacientes.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Tabla clinic
    op.create_table(
        "clinic",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column(
            "timezone",
            sa.String(length=64),
            server_default="America/Argentina/Buenos_Aires",
            nullable=False,
        ),
        sa.Column("wa_sender", sa.String(length=50), nullable=True),
        sa.Column("mp_account", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_clinic")),
    )

    # Tabla users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("rol", sa.String(length=32), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "odontologo_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinic.id"],
            name=op.f("fk_users_clinic_id_clinic"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["odontologo_id"],
            ["users.id"],
            name=op.f("fk_users_odontologo_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint(
            "clinic_id",
            "email",
            name=op.f("uq_users_clinic_id_email"),
        ),
    )
    op.create_index(op.f("ix_users_clinic_id"), "users", ["clinic_id"], unique=False)
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(op.f("ix_users_odontologo_id"), "users", ["odontologo_id"], unique=False)

    # Tabla pacientes
    op.create_table(
        "pacientes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("telefono", sa.String(length=50), nullable=False),
        sa.Column("dni", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinic.id"],
            name=op.f("fk_pacientes_clinic_id_clinic"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_pacientes")),
    )
    op.create_index(op.f("ix_pacientes_clinic_id"), "pacientes", ["clinic_id"], unique=False)
    op.create_index(op.f("ix_pacientes_telefono"), "pacientes", ["telefono"], unique=False)
    op.create_index(op.f("ix_pacientes_dni"), "pacientes", ["dni"], unique=False)
    op.create_index(
        "ix_pacientes_clinic_id_telefono",
        "pacientes",
        ["clinic_id", "telefono"],
        unique=False,
    )
    op.create_index(
        "ix_pacientes_clinic_id_dni",
        "pacientes",
        ["clinic_id", "dni"],
        unique=False,
    )

    # Tabla sillones
    op.create_table(
        "sillones",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=100), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinic.id"],
            name=op.f("fk_sillones_clinic_id_clinic"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sillones")),
    )
    op.create_index(op.f("ix_sillones_clinic_id"), "sillones", ["clinic_id"], unique=False)

    # Tabla bloqueos
    op.create_table(
        "bloqueos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paciente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("desde", sa.DateTime(timezone=True), nullable=False),
        sa.Column("hasta", sa.DateTime(timezone=True), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinic.id"],
            name=op.f("fk_bloqueos_clinic_id_clinic"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["paciente_id"],
            ["pacientes.id"],
            name=op.f("fk_bloqueos_paciente_id_pacientes"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_bloqueos")),
    )
    op.create_index(op.f("ix_bloqueos_clinic_id"), "bloqueos", ["clinic_id"], unique=False)
    op.create_index(op.f("ix_bloqueos_paciente_id"), "bloqueos", ["paciente_id"], unique=False)


def downgrade() -> None:
    op.drop_table("bloqueos")
    op.drop_table("sillones")
    op.drop_table("pacientes")
    op.drop_table("users")
    op.drop_table("clinic")
