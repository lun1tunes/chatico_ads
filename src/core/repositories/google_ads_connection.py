from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.google_ads_connection import GoogleAdsConnection
from .base import BaseRepository


class GoogleAdsConnectionRepository(BaseRepository[GoogleAdsConnection]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GoogleAdsConnection)

    async def get_by_user(self, *, user_id: str) -> GoogleAdsConnection | None:
        result = await self.session.execute(
            select(GoogleAdsConnection)
            .where(GoogleAdsConnection.user_id == user_id)
            .options(selectinload(GoogleAdsConnection.customers))
        )
        return result.scalar_one_or_none()
