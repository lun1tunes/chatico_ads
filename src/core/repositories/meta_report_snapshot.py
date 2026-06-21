from __future__ import annotations

from datetime import datetime, date
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models.meta_report_snapshot import MetaReportSnapshot


class MetaReportSnapshotRepository(BaseRepository[MetaReportSnapshot]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MetaReportSnapshot)

    async def get_latest_by_account_and_requested_days(
        self,
        *,
        meta_ad_account_id: str,
        requested_days: int,
        now: datetime,
    ) -> MetaReportSnapshot | None:
        result = await self.session.execute(
            select(MetaReportSnapshot)
            .where(
                MetaReportSnapshot.meta_ad_account_id == meta_ad_account_id,
                MetaReportSnapshot.requested_days == requested_days,
                MetaReportSnapshot.expires_at > now,
            )
            .order_by(MetaReportSnapshot.source_fetched_at.desc(), MetaReportSnapshot.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_account_and_periods(
        self,
        *,
        meta_ad_account_id: str,
        current_since: date,
        current_until: date,
        previous_since: date,
        previous_until: date,
    ) -> MetaReportSnapshot | None:
        result = await self.session.execute(
            select(MetaReportSnapshot).where(
                MetaReportSnapshot.meta_ad_account_id == meta_ad_account_id,
                MetaReportSnapshot.current_since == current_since,
                MetaReportSnapshot.current_until == current_until,
                MetaReportSnapshot.previous_since == previous_since,
                MetaReportSnapshot.previous_until == previous_until,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_snapshot(
        self,
        *,
        meta_ad_account_id: str,
        requested_days: int,
        current_since: date,
        current_until: date,
        previous_since: date,
        previous_until: date,
        payload: dict[str, object],
        source_fetched_at: datetime,
        expires_at: datetime,
    ) -> MetaReportSnapshot:
        snapshot = await self.get_by_account_and_periods(
            meta_ad_account_id=meta_ad_account_id,
            current_since=current_since,
            current_until=current_until,
            previous_since=previous_since,
            previous_until=previous_until,
        )
        if snapshot is None:
            snapshot = MetaReportSnapshot(
                id=str(uuid4()),
                meta_ad_account_id=meta_ad_account_id,
                requested_days=requested_days,
                current_since=current_since,
                current_until=current_until,
                previous_since=previous_since,
                previous_until=previous_until,
                payload=payload,
                source_fetched_at=source_fetched_at,
                expires_at=expires_at,
            )
            return await self.create(snapshot)

        snapshot.requested_days = requested_days
        snapshot.payload = payload
        snapshot.source_fetched_at = source_fetched_at
        snapshot.expires_at = expires_at
        await self.session.flush()
        return snapshot
