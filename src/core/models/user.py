from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, StringIdMixin, TimestampMixin


class User(Base, StringIdMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    locale: Mapped[str] = mapped_column(String(8), default="ru", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    sessions = relationship("AuthSession", back_populates="user", cascade="all, delete-orphan")
    meta_connections = relationship("MetaConnection", back_populates="user", cascade="all, delete-orphan")
    ai_provider_keys = relationship("UserAIProviderKey", back_populates="user", cascade="all, delete-orphan")
