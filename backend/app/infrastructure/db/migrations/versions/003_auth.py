"""Migración 003: auth - tabla refresh_token_blacklist.

`users.password_hash` y `users.activo` ya se crean en la migración 002, así que
003 solo agrega la tabla de lista negra de refresh tokens para rotación y logout.
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
    # `password_hash` y `activo` ya existen en `users` desde la migración 002.
    # Tabla refresh_token_blacklist
    op.create_table(
        "refresh_token_blacklist",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("jti", sa.String(length=255), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
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
        op.f("ix_refresh_token_blacklist_jti"), "refresh_token_blacklist", ["jti"], unique=False
    )
    op.create_index(
        op.f("ix_refresh_token_blacklist_user_id"),
        "refresh_token_blacklist",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_table("refresh_token_blacklist")
