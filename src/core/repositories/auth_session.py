from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models.auth_session import AuthSession


class AuthSessionRepository(BaseRepository[AuthSession]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AuthSession)

    async def get_active(self, session_id: str) -> AuthSession | None:
        result = await self.session.execute(
            select(AuthSession).where(AuthSession.id == session_id, AuthSession.revoked_at.is_(None))
        )
        return result.scalar_one_or_none()
