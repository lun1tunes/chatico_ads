from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, StringIdMixin, TimestampMixin


class MetaConnection(Base, StringIdMixin, TimestampMixin):
    __tablename__ = "meta_connections"
    __table_args__ = (UniqueConstraint("user_id", "meta_user_id", name="uq_meta_connection_user_meta_user"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    meta_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    meta_user_name: Mapped[str] = mapped_column(String(255), nullable=False)
    access_token_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scopes: Mapped[str] = mapped_column(String(512), default="", nullable=False)

    user = relationship("User", back_populates="meta_connections")
    ad_accounts = relationship("MetaAdAccount", back_populates="connection", cascade="all, delete-orphan")
