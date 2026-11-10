"""Migración 004: catálogo de prácticas, aranceles y auditoría de seña (C-04).

Crea las tablas tipos_practica, aranceles y auditorias_sena con sus CHECKs,
UNIQUE e índices. Depende de 003 (auth), no reutiliza esa revisión.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tipos_practica",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("nombre", sa.String(length=200), nullable=False),
        sa.Column("duracion_min", sa.Integer(), nullable=False),
        sa.Column("precio_base", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("sena_pct", sa.Integer(), server_default="0", nullable=False),
        sa.Column("activa", sa.Boolean(), server_default="true", nullable=False),
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
        sa.CheckConstraint(
            "duracion_min > 0", name=op.f("ck_tipos_practica_duracion_min_positiva")
        ),
        sa.CheckConstraint(
            "precio_base >= 0", name=op.f("ck_tipos_practica_precio_base_no_negativo")
        ),
        sa.CheckConstraint(
            "sena_pct >= 0 AND sena_pct <= 100", name=op.f("ck_tipos_practica_sena_pct_rango")
        ),
        sa.ForeignKeyConstraint(
            ["clinic_id"],
            ["clinic.id"],
            name=op.f("fk_tipos_practica_clinic_id_clinic"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_tipos_practica")),
        sa.UniqueConstraint("clinic_id", "nombre", name=op.f("uq_tipos_practica_clinic_id_nombre")),
    )
    op.create_index(
        op.f("ix_tipos_practica_clinic_id"), "tipos_practica", ["clinic_id"], unique=False
    )
    op.create_index(
        "ix_tipos_practica_clinic_id_activa",
        "tipos_practica",
        ["clinic_id", "activa"],
        unique=False,
    )

    op.create_table(
        "aranceles",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo_practica_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("precio", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("sena_pct", sa.Integer(), nullable=False),
        sa.Column("vigente_desde", sa.Date(), nullable=False),
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
        sa.CheckConstraint("precio >= 0", name=op.f("ck_aranceles_precio_no_negativo")),
        sa.CheckConstraint(
            "sena_pct >= 0 AND sena_pct <= 100", name=op.f("ck_aranceles_sena_pct_rango")
        ),
        sa.ForeignKeyConstraint(
            ["tipo_practica_id"],
            ["tipos_practica.id"],
            name=op.f("fk_aranceles_tipo_practica_id_tipos_practica"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_aranceles")),
        sa.UniqueConstraint("tipo_practica_id", name=op.f("uq_aranceles_tipo_practica_id")),
    )
    op.create_index(
        op.f("ix_aranceles_tipo_practica_id"), "aranceles", ["tipo_practica_id"], unique=False
    )

    op.create_table(
        "auditorias_sena",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("clinic_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("tipo_practica_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("usuario_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("valor_anterior", sa.Integer(), nullable=False),
        sa.Column("valor_nuevo", sa.Integer(), nullable=False),
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
            name=op.f("fk_auditorias_sena_clinic_id_clinic"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tipo_practica_id"],
            ["tipos_practica.id"],
            name=op.f("fk_auditorias_sena_tipo_practica_id_tipos_practica"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["usuario_id"],
            ["users.id"],
            name=op.f("fk_auditorias_sena_usuario_id_users"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_auditorias_sena")),
    )
    op.create_index(
        op.f("ix_auditorias_sena_clinic_id"), "auditorias_sena", ["clinic_id"], unique=False
    )
    op.create_index(
        op.f("ix_auditorias_sena_tipo_practica_id"),
        "auditorias_sena",
        ["tipo_practica_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_auditorias_sena_usuario_id"), "auditorias_sena", ["usuario_id"], unique=False
    )
    op.create_index(
        "ix_auditorias_sena_clinic_tipo_created",
        "auditorias_sena",
        ["clinic_id", "tipo_practica_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("auditorias_sena")
    op.drop_table("aranceles")
    op.drop_table("tipos_practica")
