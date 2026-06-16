from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models.meta_connection import MetaConnection


class MetaConnectionRepository(BaseRepository[MetaConnection]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MetaConnection)

    async def get_by_user_and_meta_user(self, *, user_id: str, meta_user_id: str) -> MetaConnection | None:
        result = await self.session.execute(
            select(MetaConnection)
            .where(MetaConnection.user_id == user_id, MetaConnection.meta_user_id == meta_user_id)
            .options(selectinload(MetaConnection.ad_accounts))
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[MetaConnection]:
        result = await self.session.execute(
            select(MetaConnection)
            .where(MetaConnection.user_id == user_id)
            .options(selectinload(MetaConnection.ad_accounts))
            .order_by(MetaConnection.created_at.desc())
        )
        return list(result.scalars().all())
