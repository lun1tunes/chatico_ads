from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, StringIdMixin, TimestampMixin


class GoogleAdsCustomer(Base, StringIdMixin, TimestampMixin):
    __tablename__ = "google_ads_customers"
    __table_args__ = (
        UniqueConstraint("connection_id", "external_customer_id", name="uq_google_ads_customer_connection_external"),
    )

    connection_id: Mapped[str] = mapped_column(
        ForeignKey("google_ads_connections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    external_customer_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    resource_name: Mapped[str] = mapped_column(String(64), nullable=False)
    descriptive_name: Mapped[str] = mapped_column(String(255), nullable=False)
    currency_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    time_zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    is_manager: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_directly_accessible: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    hierarchy_level: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    root_customer_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    manager_customer_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    login_customer_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    connection = relationship("GoogleAdsConnection", back_populates="customers")
