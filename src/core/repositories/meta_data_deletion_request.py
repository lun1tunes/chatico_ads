from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models.meta_data_deletion_request import MetaDataDeletionRequest


class MetaDataDeletionRequestRepository(BaseRepository[MetaDataDeletionRequest]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MetaDataDeletionRequest)
