from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .base import BaseRepository
from ..models.meta_ad_account import MetaAdAccount
from ..models.meta_connection import MetaConnection


class MetaAdAccountRepository(BaseRepository[MetaAdAccount]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MetaAdAccount)

    async def list_for_user(self, user_id: str) -> list[MetaAdAccount]:
        result = await self.session.execute(
            select(MetaAdAccount)
            .join(MetaAdAccount.connection)
            .where(MetaConnection.user_id == user_id)
            .options(selectinload(MetaAdAccount.connection))
            .order_by(MetaAdAccount.name.asc())
        )
        return list(result.scalars().all())

    async def get_for_user(self, *, user_id: str, external_id: str) -> MetaAdAccount | None:
        result = await self.session.execute(
            select(MetaAdAccount)
            .join(MetaAdAccount.connection)
            .where(MetaConnection.user_id == user_id, MetaAdAccount.external_id == external_id)
            .options(selectinload(MetaAdAccount.connection))
        )
        return result.scalar_one_or_none()

    async def delete(self, entity: MetaAdAccount) -> None:
        await self.session.execute(delete(MetaAdAccount).where(MetaAdAccount.id == entity.id))
