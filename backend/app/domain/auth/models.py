"""Modelos del dominio auth: RefreshTokenBlacklist."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.mixins import AuditMixin
from app.infrastructure.db.base import Base


class RefreshTokenBlacklist(Base, AuditMixin):
    """Lista negra de refresh tokens revocados (logout o rotación)."""

    __tablename__ = "refresh_token_blacklist"

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
    )
    jti: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
