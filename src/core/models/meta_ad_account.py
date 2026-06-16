from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, StringIdMixin, TimestampMixin


class MetaAdAccount(Base, StringIdMixin, TimestampMixin):
    __tablename__ = "meta_ad_accounts"
    __table_args__ = (UniqueConstraint("connection_id", "external_id", name="uq_meta_ad_account_connection_external"),)

    connection_id: Mapped[str] = mapped_column(
        ForeignKey("meta_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    account_id: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    timezone_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    account_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    connection = relationship("MetaConnection", back_populates="ad_accounts")
