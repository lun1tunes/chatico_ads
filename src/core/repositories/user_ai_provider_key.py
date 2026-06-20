from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models.user_ai_provider_key import UserAIProviderKey


class UserAIProviderKeyRepository(BaseRepository[UserAIProviderKey]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, UserAIProviderKey)

    async def get_by_user_and_provider(self, *, user_id: str, provider: str) -> UserAIProviderKey | None:
        result = await self.session.execute(
            select(UserAIProviderKey).where(
                UserAIProviderKey.user_id == user_id,
                UserAIProviderKey.provider == provider,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, *, user_id: str) -> list[UserAIProviderKey]:
        result = await self.session.execute(
            select(UserAIProviderKey)
            .where(UserAIProviderKey.user_id == user_id)
            .order_by(UserAIProviderKey.provider.asc())
        )
        return list(result.scalars().all())

    async def delete(self, entity: UserAIProviderKey) -> None:
        await self.session.delete(entity)
