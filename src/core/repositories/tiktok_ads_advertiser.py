from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.tiktok_ads_advertiser import TikTokAdsAdvertiser
from ..models.tiktok_ads_connection import TikTokAdsConnection
from .base import BaseRepository


class TikTokAdsAdvertiserRepository(BaseRepository[TikTokAdsAdvertiser]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, TikTokAdsAdvertiser)

    async def get_for_user(self, *, user_id: str, external_advertiser_id: str) -> TikTokAdsAdvertiser | None:
        result = await self.session.execute(
            select(TikTokAdsAdvertiser)
            .join(TikTokAdsAdvertiser.connection)
            .where(
                TikTokAdsConnection.user_id == user_id,
                TikTokAdsAdvertiser.advertiser_id == external_advertiser_id,
            )
            .options(selectinload(TikTokAdsAdvertiser.connection).selectinload(TikTokAdsConnection.advertisers))
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[TikTokAdsAdvertiser]:
        result = await self.session.execute(
            select(TikTokAdsAdvertiser)
            .join(TikTokAdsAdvertiser.connection)
            .where(TikTokAdsConnection.user_id == user_id)
            .options(selectinload(TikTokAdsAdvertiser.connection))
            .order_by(TikTokAdsAdvertiser.name.asc(), TikTokAdsAdvertiser.advertiser_id.asc())
        )
        return list(result.scalars().all())

    async def delete(self, entity: TikTokAdsAdvertiser) -> None:
        await self.session.delete(entity)
