from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import settings


class DatabaseHelper:
    def __init__(self) -> None:
        self.engine = create_async_engine(settings.database_url, echo=settings.debug, future=True)
        self.session_factory = async_sessionmaker(self.engine, expire_on_commit=False, class_=AsyncSession)

    async def scoped_session_dependency(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            yield session


db_helper = DatabaseHelper()
