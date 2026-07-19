from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.models.db_helper import db_helper
from core.models.tiktok_ads_advertiser import TikTokAdsAdvertiser
from core.models.tiktok_ads_connection import TikTokAdsConnection
from core.models.user import User
from core.security.encryption_service import EncryptionService
from core.services.date_range_service import DateRangeService
from core.services.tiktok_ads_report_service import TikTokAdsReportService
from core.use_cases.dashboard import GenerateTikTokAdsReportUseCase
from core.utils.ai_context import build_report_context


class FixedDateRangeService:
    def __init__(self, *, anchor: datetime | None = None) -> None:
        self.anchor = anchor or datetime(2026, 6, 15, tzinfo=timezone.utc)

    def build_periods(self, *, days: int, now=None):
        return DateRangeService().build_periods(days=days, now=self.anchor)


class FakeTikTokAdsReportClient:
    def __init__(self) -> None:
        self.refresh_calls = 0
        self.advertiser_info_calls = 0
        self.report_calls: list[tuple[str, str]] = []
        self.campaign_calls = 0
        self.ad_calls = 0

    async def refresh_access_token(self, *, refresh_token: str) -> dict[str, object]:
        self.refresh_calls += 1
        assert refresh_token == "tiktok-refresh-token"
        return {"access_token": "tiktok-access-token", "expires_in": 3600}

    async def get_advertiser_info(
        self,
        *,
        advertiser_ids: list[str],
        access_token: str,
    ) -> list[dict[str, object]]:
        self.advertiser_info_calls += 1
        assert advertiser_ids == ["1234567890123456789"]
        assert access_token == "tiktok-access-token"
        return [
            {
                "advertiser_id": "1234567890123456789",
                "name": "TikTok Main Advertiser",
                "currency": "USD",
                "timezone": "America/New_York",
            }
        ]

    async def get_integrated_report(
        self,
        *,
        advertiser_id: str,
        access_token: str,
        data_level: str,
        dimensions: list[str],
        metrics: list[str],
        start_date: str,
        end_date: str,
    ) -> dict[str, object]:
        self.report_calls.append((data_level, start_date))
        assert advertiser_id == "1234567890123456789"
        assert access_token == "tiktok-access-token"
        assert "conversion" in metrics

        if data_level == "ADVERTISER":
            if dimensions == ["stat_time_day"]:
                if start_date == "2026-05-17":
                    return {
                        "rows": [
                            {
                                "dimensions": {"stat_time_day": "2026-05-17"},
                                "metrics": {
                                    "spend": "60.0",
                                    "impressions": "3000",
                                    "clicks": "100",
                                    "conversion": "6",
                                },
                            },
                            {
                                "dimensions": {"stat_time_day": "2026-05-18"},
                                "metrics": {
                                    "spend": "120.0",
                                    "impressions": "7000",
                                    "clicks": "220",
                                    "conversion": "12",
                                },
                            },
                        ],
                        "total_metrics": {},
                    }
                return {
                    "rows": [
                        {
                            "dimensions": {"stat_time_day": "2026-04-17"},
                            "metrics": {
                                "spend": "50.0",
                                "impressions": "2500",
                                "clicks": "90",
                                "conversion": "5",
                            },
                        },
                        {
                            "dimensions": {"stat_time_day": "2026-04-18"},
                            "metrics": {
                                "spend": "70.0",
                                "impressions": "4500",
                                "clicks": "150",
                                "conversion": "7",
                            },
                        },
                    ],
                    "total_metrics": {},
                }
            if start_date == "2026-05-17":
                return {
                    "rows": [],
                    "total_metrics": {
                        "spend": "180.0",
                        "reach": "9000",
                        "impressions": "16000",
                        "clicks": "320",
                        "conversion": "18",
                    },
                }
            return {
                "rows": [],
                "total_metrics": {
                    "spend": "120.0",
                    "reach": "7000",
                    "impressions": "12000",
                    "clicks": "240",
                    "conversion": "12",
                },
            }

        if data_level == "CAMPAIGN":
            if start_date == "2026-05-17":
                return {
                    "rows": [
                        {
                            "dimensions": {"campaign_id": "cmp_1"},
                            "metrics": {
                                "spend": "150.0",
                                "reach": "8000",
                                "impressions": "12000",
                                "clicks": "260",
                                "conversion": "15",
                            },
                        },
                        {
                            "dimensions": {"campaign_id": "cmp_2"},
                            "metrics": {
                                "spend": "30.0",
                                "reach": "1000",
                                "impressions": "4000",
                                "clicks": "60",
                                "conversion": "3",
                            },
                        },
                    ],
                    "total_metrics": {},
                }
            return {
                "rows": [
                    {
                        "dimensions": {"campaign_id": "cmp_1"},
                        "metrics": {
                            "spend": "100.0",
                            "reach": "6000",
                            "impressions": "9000",
                            "clicks": "200",
                            "conversion": "10",
                        },
                    },
                    {
                        "dimensions": {"campaign_id": "cmp_2"},
                        "metrics": {
                            "spend": "20.0",
                            "reach": "1000",
                            "impressions": "3000",
                            "clicks": "40",
                            "conversion": "2",
                        },
                    },
                ],
                "total_metrics": {},
            }

        return {
            "rows": [
                {
                    "dimensions": {"campaign_id": "cmp_1", "ad_id": "ad_1"},
                    "metrics": {
                        "spend": "60.0",
                        "impressions": "6000",
                        "clicks": "120",
                        "conversion": "7",
                    },
                },
                {
                    "dimensions": {"campaign_id": "cmp_1", "ad_id": "ad_2"},
                    "metrics": {
                        "spend": "40.0",
                        "impressions": "3000",
                        "clicks": "80",
                        "conversion": "3",
                    },
                },
                {
                    "dimensions": {"campaign_id": "cmp_2", "ad_id": "ad_3"},
                    "metrics": {
                        "spend": "20.0",
                        "impressions": "3000",
                        "clicks": "40",
                        "conversion": "2",
                    },
                },
            ],
            "total_metrics": {},
        }

    async def list_campaigns(self, *, advertiser_id: str, access_token: str) -> list[dict[str, object]]:
        self.campaign_calls += 1
        return [
            {"campaign_id": "cmp_1", "campaign_name": "Always On", "operation_status": "ENABLE"},
            {"campaign_id": "cmp_2", "campaign_name": "Retargeting", "operation_status": "DISABLE"},
        ]

    async def list_ads(self, *, advertiser_id: str, access_token: str) -> list[dict[str, object]]:
        self.ad_calls += 1
        return [
            {"ad_id": "ad_1", "ad_name": "Spark Ad 1", "ad_format": "SPARK_AD"},
            {"ad_id": "ad_2", "ad_name": "Spark Ad 2", "ad_format": "SPARK_AD"},
            {"ad_id": "ad_3", "ad_name": "Collection Ad", "ad_format": "COLLECTION_AD"},
        ]


@pytest.mark.unit
@pytest.mark.service
async def test_generate_tiktok_ads_report_use_case_builds_dashboard_payload(db_session):
    encryption_service = EncryptionService()
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="en"))
    db_session.add(
        TikTokAdsConnection(
            id="tiktok-conn-1",
            user_id="user-1",
            refresh_token_encrypted=encryption_service.encrypt("tiktok-refresh-token"),
            access_token_encrypted=encryption_service.encrypt("stale-access-token"),
            scopes="ads.read,reporting",
        )
    )
    db_session.add(
        TikTokAdsAdvertiser(
            id="tiktok-advertiser-1",
            connection_id="tiktok-conn-1",
            advertiser_id="1234567890123456789",
            name="Stored advertiser",
            currency="USD",
            timezone_name="America/New_York",
        )
    )
    await db_session.commit()

    fake_client = FakeTikTokAdsReportClient()
    use_case = GenerateTikTokAdsReportUseCase(
        session=db_session,
        date_range_service=FixedDateRangeService(),
        report_service=TikTokAdsReportService(
            tiktok_ads_client=fake_client,
            encryption_service=encryption_service,
        ),
    )

    report = await use_case.execute(user_id="user-1", advertiser_id="1234567890123456789", days=30)

    assert report["account"]["name"] == "TikTok Main Advertiser"
    assert report["summary"]["active_campaigns"] == 1
    assert report["summary"]["metrics"]["spend"]["current"] == 180.0
    assert report["summary"]["metrics"]["reach"]["current"] == 9000
    assert report["summary"]["metrics"]["results"]["current"] == 18.0
    assert report["trend"]["current"][0] == {
        "date": "2026-05-17",
        "spend": 60.0,
        "results": 6.0,
        "impressions": 3000,
    }
    assert report["trend"]["previous"][-1]["date"] == "2026-04-18"
    assert report["campaigns"][0]["name"] == "Always On"
    assert report["campaigns"][0]["metrics"]["cpc"]["current"] == 150.0 / 260.0
    assert report["campaigns"][0]["creatives"][0]["name"] == "Spark Ad 1"
    assert report["campaigns"][0]["creatives"][0]["metrics"]["ctr"] == 2.0
    assert report["campaigns"][1]["creatives"][0]["object_type"] == "COLLECTION_AD"

    async with db_helper.session_factory() as verification_session:
        stored_advertiser = await verification_session.get(TikTokAdsAdvertiser, "tiktok-advertiser-1")
        stored_connection = await verification_session.get(TikTokAdsConnection, "tiktok-conn-1")
        assert stored_advertiser is not None
        assert stored_advertiser.last_synced_at is not None
        assert stored_connection is not None
        assert encryption_service.decrypt(stored_connection.access_token_encrypted) == "tiktok-access-token"

    context = build_report_context(report)
    assert "acct|TikTok Main Advertiser|1234567890123456789|USD|America/New_York" in context
    assert "sum|conversions|1|2|sp:180,120,50" in context
    assert "cmp|Always On|ENABLE|conversions|" in context
    assert "crt|Spark Ad 1|SPARK_AD|60|6000|120|2|7|conversions" in context

    assert fake_client.refresh_calls == 1
    assert fake_client.advertiser_info_calls == 1
    assert fake_client.campaign_calls == 1
    assert fake_client.ad_calls == 1
