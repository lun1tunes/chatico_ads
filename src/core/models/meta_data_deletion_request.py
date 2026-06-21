from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, StringIdMixin, TimestampMixin


class MetaDataDeletionRequest(Base, StringIdMixin, TimestampMixin):
    __tablename__ = "meta_data_deletion_requests"

    meta_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    detail: Mapped[str] = mapped_column(String(512), nullable=False, default="")
    deleted_users_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
