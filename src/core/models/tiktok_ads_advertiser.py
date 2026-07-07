from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, StringIdMixin, TimestampMixin


class TikTokAdsAdvertiser(Base, StringIdMixin, TimestampMixin):
    __tablename__ = "tiktok_ads_advertisers"
    __table_args__ = (
        UniqueConstraint("connection_id", "advertiser_id", name="uq_tiktok_ads_advertiser_connection_external"),
    )

    connection_id: Mapped[str] = mapped_column(
        ForeignKey("tiktok_ads_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    advertiser_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    timezone_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    connection = relationship("TikTokAdsConnection", back_populates="advertisers")
