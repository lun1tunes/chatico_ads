from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, StringIdMixin, TimestampMixin


class MetaReportSnapshot(Base, StringIdMixin, TimestampMixin):
    __tablename__ = "meta_report_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "meta_ad_account_id",
            "current_since",
            "current_until",
            "previous_since",
            "previous_until",
            name="uq_meta_report_snapshot_account_period",
        ),
    )

    meta_ad_account_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("meta_ad_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    requested_days: Mapped[int] = mapped_column(Integer, nullable=False)
    current_since: Mapped[date] = mapped_column(Date, nullable=False)
    current_until: Mapped[date] = mapped_column(Date, nullable=False)
    previous_since: Mapped[date] = mapped_column(Date, nullable=False)
    previous_until: Mapped[date] = mapped_column(Date, nullable=False)
    payload: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    source_fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    ad_account = relationship("MetaAdAccount", back_populates="report_snapshots")
