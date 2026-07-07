from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.tiktok_ads_connection import TikTokAdsConnection
from .base import BaseRepository


class TikTokAdsConnectionRepository(BaseRepository[TikTokAdsConnection]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TikTokAdsConnection)

    async def get_by_user(self, *, user_id: str) -> TikTokAdsConnection | None:
        result = await self.session.execute(
            select(TikTokAdsConnection)
            .where(TikTokAdsConnection.user_id == user_id)
            .options(selectinload(TikTokAdsConnection.advertisers))
        )
        return result.scalar_one_or_none()
