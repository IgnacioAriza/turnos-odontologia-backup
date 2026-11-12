"""Migración 006: campos de gestión de turnos (C-06).

Agrega `turnos.sena_perdida` (NOT NULL, default false) para marcar la seña
retenida cuando se cancela o reprograma fuera de la ventana de 12 horas, y
`turnos.reprogramado_de_id` (nullable, FK a `turnos.id` con ON DELETE SET NULL)
para encadenar la reprogramación que exige una nueva seña.

Depende de 005 (motor de turnos).
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "turnos",
        sa.Column("sena_perdida", sa.Boolean(), server_default="false", nullable=False),
    )
    op.add_column(
        "turnos",
        sa.Column("reprogramado_de_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        op.f("ix_turnos_reprogramado_de_id"),
        "turnos",
        ["reprogramado_de_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("fk_turnos_reprogramado_de_id_turnos"),
        "turnos",
        "turnos",
        ["reprogramado_de_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(op.f("fk_turnos_reprogramado_de_id_turnos"), "turnos", type_="foreignkey")
    op.drop_index(op.f("ix_turnos_reprogramado_de_id"), table_name="turnos")
    op.drop_column("turnos", "reprogramado_de_id")
    op.drop_column("turnos", "sena_perdida")
