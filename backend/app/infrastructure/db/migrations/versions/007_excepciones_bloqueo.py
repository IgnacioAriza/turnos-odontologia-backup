"""Migración 007: tabla `excepciones_bloqueo` (C-07).

Registra de forma durable cada excepción al bloqueo por ausentismo que autoriza
recepción/admin: una fila por turno creado, con el motivo y el usuario que la
decidió (RN-AUS-02). `UNIQUE(turno_id)` evita duplicados por reintento.

Depende de 006 (gestión de turnos).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "excepciones_bloqueo",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paciente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("turno_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=False),
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
            name=op.f("fk_excepciones_bloqueo_clinic_id_clinic"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["paciente_id"],
            ["pacientes.id"],
            name=op.f("fk_excepciones_bloqueo_paciente_id_pacientes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["turno_id"],
            ["turnos.id"],
            name=op.f("fk_excepciones_bloqueo_turno_id_turnos"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["users.id"],
            name=op.f("fk_excepciones_bloqueo_usuario_id_users"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_excepciones_bloqueo")),
        sa.UniqueConstraint("turno_id", name=op.f("uq_excepciones_bloqueo_turno_id")),
    )
    op.create_index(
        "ix_excepciones_bloqueo_clinic_created",
        "excepciones_bloqueo",
        ["clinic_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_excepciones_bloqueo_paciente",
        "excepciones_bloqueo",
        ["paciente_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_excepciones_bloqueo_paciente", table_name="excepciones_bloqueo")
    op.drop_index("ix_excepciones_bloqueo_clinic_created", table_name="excepciones_bloqueo")
    op.drop_table("excepciones_bloqueo")
