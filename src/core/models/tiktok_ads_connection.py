from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, StringIdMixin, TimestampMixin


class TikTokAdsConnection(Base, StringIdMixin, TimestampMixin):
    __tablename__ = "tiktok_ads_connections"
    __table_args__ = (UniqueConstraint("user_id", name="uq_tiktok_ads_connection_user"),)

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    refresh_token_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    access_token_encrypted: Mapped[str] = mapped_column(String, nullable=False)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    scopes: Mapped[str] = mapped_column(String(1024), default="", nullable=False)

    user = relationship("User", back_populates="tiktok_ads_connections")
    advertisers = relationship("TikTokAdsAdvertiser", back_populates="connection", cascade="all, delete-orphan")
