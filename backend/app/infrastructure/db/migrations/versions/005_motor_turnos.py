"""Migración 005: motor de turnos, horarios de atención y ajustes de pacientes (C-05).

Crea las tablas `horarios_atencion` y `turnos`, agrega los constraints
anti-solape por sillón y odontólogo con `EXCLUDE USING gist` (Postgres) y
ajusta `pacientes` para la reserva pública: `dni` nullable, `bloqueado_hasta`,
`faltas_count` y UNIQUE `(clinic_id, telefono)`.

Depende de 004 (catálogo), no reutiliza esa revisión.
"""

from typing import Any

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

ESTADOS_VIGENTES = "'pendiente_sena', 'confirmado', 'reprogramado'"
ESTADOS_TODOS = (
    "'pendiente_sena', 'confirmado', 'cancelado', 'reprogramado', 'completado', 'ausente'"
)


def _timestamps() -> list[sa.Column[Any]]:
    return [
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
    ]


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    # --- pacientes: reserva pública por teléfono y bloqueo por faltas ---
    op.alter_column(
        "pacientes",
        "dni",
        existing_type=sa.String(length=20),
        nullable=True,
    )
    op.add_column(
        "pacientes",
        sa.Column("faltas_count", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "pacientes",
        sa.Column("bloqueado_hasta", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_pacientes_clinic_id_telefono", "pacientes", ["clinic_id", "telefono"]
    )
    op.create_index("ix_pacientes_clinic_id_dni", "pacientes", ["clinic_id", "dni"], unique=False)

    # --- horarios de atención ---
    op.create_table(
        "horarios_atencion",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("dia_semana", sa.SmallInteger(), nullable=False),
        sa.Column("hora_desde", sa.Time(), nullable=False),
        sa.Column("hora_hasta", sa.Time(), nullable=False),
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "dia_semana >= 0 AND dia_semana <= 6",
            name=op.f("ck_horarios_atencion_dia_semana_rango"),
        ),
        sa.CheckConstraint(
            "hora_hasta > hora_desde", name=op.f("ck_horarios_atencion_hora_hasta_mayor")
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinic.id"],
            name=op.f("fk_horarios_atencion_clinic_id_clinic"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_horarios_atencion")),
        sa.UniqueConstraint(
            "clinic_id",
            "dia_semana",
            "hora_desde",
            name="uq_horarios_atencion_clinic_dia_hora",
        ),
    )
    op.create_index(
        op.f("ix_horarios_atencion_clinic_id"),
        "horarios_atencion",
        ["clinic_id"],
        unique=False,
    )

    # --- turnos ---
    op.create_table(
        "turnos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("paciente_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sillon_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("odontologo_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo_practica_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("inicio", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fin", sa.DateTime(timezone=True), nullable=False),
        sa.Column("estado", sa.String(length=32), server_default="pendiente_sena", nullable=False),
        sa.Column("manage_token", sa.String(length=64), nullable=True),
        sa.Column("reprogramaciones_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "monto_sena", sa.Numeric(precision=12, scale=2), server_default="0", nullable=False
        ),
        sa.Column("expira_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.CheckConstraint("fin > inicio", name=op.f("ck_turnos_fin_mayor_inicio")),
        sa.CheckConstraint("monto_sena >= 0", name=op.f("ck_turnos_monto_sena_no_negativo")),
        sa.CheckConstraint(f"estado IN ({ESTADOS_TODOS})", name=op.f("ck_turnos_estado_valido")),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinic.id"],
            name=op.f("fk_turnos_clinic_id_clinic"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["paciente_id"],
            ["pacientes.id"],
            name=op.f("fk_turnos_paciente_id_pacientes"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["sillon_id"],
            ["sillones.id"],
            name=op.f("fk_turnos_sillon_id_sillones"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["odontologo_id"],
            ["users.id"],
            name=op.f("fk_turnos_odontologo_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tipo_practica_id"],
            ["tipos_practica.id"],
            name=op.f("fk_turnos_tipo_practica_id_tipos_practica"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_turnos")),
        sa.UniqueConstraint("manage_token", name="uq_turnos_manage_token"),
    )
    op.create_index(op.f("ix_turnos_clinic_id"), "turnos", ["clinic_id"], unique=False)
    op.create_index(op.f("ix_turnos_paciente_id"), "turnos", ["paciente_id"], unique=False)
    op.create_index(op.f("ix_turnos_sillon_id"), "turnos", ["sillon_id"], unique=False)
    op.create_index(op.f("ix_turnos_odontologo_id"), "turnos", ["odontologo_id"], unique=False)
    op.create_index(
        op.f("ix_turnos_tipo_practica_id"), "turnos", ["tipo_practica_id"], unique=False
    )
    op.create_index("ix_turnos_clinic_inicio", "turnos", ["clinic_id", "inicio"], unique=False)
    op.create_index("ix_turnos_sillon_inicio", "turnos", ["sillon_id", "inicio"], unique=False)
    op.create_index(
        "ix_turnos_odontologo_inicio", "turnos", ["odontologo_id", "inicio"], unique=False
    )
    op.create_index("ix_turnos_paciente_inicio", "turnos", ["paciente_id", "inicio"], unique=False)
    op.create_index("ix_turnos_estado", "turnos", ["estado"], unique=False)
    op.create_index("ix_turnos_estado_expira", "turnos", ["estado", "expira_at"], unique=False)

    op.execute(
        "ALTER TABLE turnos ADD CONSTRAINT ex_turnos_sillon_solape "
        "EXCLUDE USING gist (sillon_id WITH =, tstzrange(inicio, fin, '[)') WITH &&) "
        f"WHERE (estado IN ({ESTADOS_VIGENTES}))"
    )
    op.execute(
        "ALTER TABLE turnos ADD CONSTRAINT ex_turnos_odontologo_solape "
        "EXCLUDE USING gist (odontologo_id WITH =, tstzrange(inicio, fin, '[)') WITH &&) "
        f"WHERE (estado IN ({ESTADOS_VIGENTES}))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE turnos DROP CONSTRAINT IF EXISTS ex_turnos_odontologo_solape")
    op.execute("ALTER TABLE turnos DROP CONSTRAINT IF EXISTS ex_turnos_sillon_solape")

    op.drop_index("ix_turnos_estado_expira", table_name="turnos")
    op.drop_index("ix_turnos_estado", table_name="turnos")
    op.drop_index("ix_turnos_paciente_inicio", table_name="turnos")
    op.drop_index("ix_turnos_odontologo_inicio", table_name="turnos")
    op.drop_index("ix_turnos_sillon_inicio", table_name="turnos")
    op.drop_index("ix_turnos_clinic_inicio", table_name="turnos")
    op.drop_index(op.f("ix_turnos_tipo_practica_id"), table_name="turnos")
    op.drop_index(op.f("ix_turnos_odontologo_id"), table_name="turnos")
    op.drop_index(op.f("ix_turnos_sillon_id"), table_name="turnos")
    op.drop_index(op.f("ix_turnos_paciente_id"), table_name="turnos")
    op.drop_index(op.f("ix_turnos_clinic_id"), table_name="turnos")
    op.drop_table("turnos")

    op.drop_index(op.f("ix_horarios_atencion_clinic_id"), table_name="horarios_atencion")
    op.drop_table("horarios_atencion")

    op.drop_index("ix_pacientes_clinic_id_dni", table_name="pacientes")
    op.drop_constraint("uq_pacientes_clinic_id_telefono", "pacientes", type_="unique")
    op.drop_column("pacientes", "bloqueado_hasta")
    op.drop_column("pacientes", "faltas_count")
    op.alter_column(
        "pacientes",
        "dni",
        existing_type=sa.String(length=20),
        nullable=False,
    )
