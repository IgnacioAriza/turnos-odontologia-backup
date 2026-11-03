"""Migración 003: auth - password_hash, activo en users, tabla refresh_token_blacklist.

Agrega columnas de autenticación a la tabla users y crea la tabla de lista negra
de refresh tokens para rotación y logout.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Agregar columnas a users (password_hash ya estaba en el modelo pero no en la migración 002)
    op.add_column(
        "users",
        sa.Column("password_hash", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "users",
        sa.Column("activo", sa.Boolean(), server_default="true", nullable=False),
    )

    # Tabla refresh_token_blacklist
    op.create_table(
        "refresh_token_blacklist",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("jti", sa.String(length=255), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
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
            ["user_id"],
            ["users.id"],
            name=op.f("fk_refresh_token_blacklist_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_refresh_token_blacklist")),
        sa.UniqueConstraint("jti", name=op.f("uq_refresh_token_blacklist_jti")),
    )
    op.create_index(
        op.f("ix_refresh_token_blacklist_jti"),
        "refresh_token_blacklist",
        ["jti"],
        unique=False,
    )
    op.create_index(
        op.f("ix_refresh_token_blacklist_user_id"),
        "refresh_token_blacklist",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("refresh_token_blacklist")
    op.drop_column("users", "activo")
    op.drop_column("users", "password_hash")
