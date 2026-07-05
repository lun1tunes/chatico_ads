from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.google_ads_connection import GoogleAdsConnection
from ..models.google_ads_customer import GoogleAdsCustomer
from .base import BaseRepository


class GoogleAdsCustomerRepository(BaseRepository[GoogleAdsCustomer]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GoogleAdsCustomer)

    async def get_for_user(self, *, user_id: str, external_customer_id: str) -> GoogleAdsCustomer | None:
        result = await self.session.execute(
            select(GoogleAdsCustomer)
            .join(GoogleAdsCustomer.connection)
            .where(
                GoogleAdsConnection.user_id == user_id,
                GoogleAdsCustomer.external_customer_id == external_customer_id,
            )
            .options(selectinload(GoogleAdsCustomer.connection))
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[GoogleAdsCustomer]:
        result = await self.session.execute(
            select(GoogleAdsCustomer)
            .join(GoogleAdsCustomer.connection)
            .where(GoogleAdsConnection.user_id == user_id)
            .options(selectinload(GoogleAdsCustomer.connection))
            .order_by(
                GoogleAdsCustomer.is_directly_accessible.desc(),
                GoogleAdsCustomer.is_manager.desc(),
                GoogleAdsCustomer.descriptive_name.asc(),
            )
        )
        return list(result.scalars().all())

    async def delete(self, entity: GoogleAdsCustomer) -> None:
        await self.session.delete(entity)
