from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.models.db_helper import db_helper
from core.models.google_ads_connection import GoogleAdsConnection
from core.models.google_ads_customer import GoogleAdsCustomer
from core.models.user import User
from core.security.encryption_service import EncryptionService
from core.services.date_range_service import DateRangeService
from core.services.google_ads_report_service import GoogleAdsReportService
from core.use_cases.dashboard import GenerateGoogleAdsReportUseCase
from core.utils.ai_context import build_report_context


class FixedDateRangeService:
    def __init__(self, *, anchor: datetime | None = None) -> None:
        self.anchor = anchor or datetime(2026, 6, 15, tzinfo=timezone.utc)

    def build_periods(self, *, days: int, now=None):
        return DateRangeService().build_periods(days=days, now=self.anchor)


class FakeGoogleAdsReportClient:
    def __init__(self) -> None:
        self.refresh_calls = 0
        self.customer_calls = 0
        self.campaign_calls = 0
        self.summary_calls = 0
        self.campaign_metric_calls = 0
        self.ad_metric_calls = 0

    async def refresh_access_token(self, *, refresh_token: str) -> dict[str, object]:
        self.refresh_calls += 1
        assert refresh_token == "google-refresh-token"
        return {"access_token": "google-access-token", "expires_in": 3600}

    async def get_customer(
        self,
        *,
        customer_id: str,
        access_token: str,
        login_customer_id: str | None = None,
    ) -> dict[str, object]:
        self.customer_calls += 1
        assert customer_id == "1234567890"
        assert access_token == "google-access-token"
        assert login_customer_id == "9988776655"
        return {
            "customer": {
                "id": "1234567890",
                "descriptiveName": "Google Main Account",
                "currencyCode": "USD",
                "timeZone": "America/New_York",
            }
        }

    async def list_campaigns(
        self,
        *,
        customer_id: str,
        access_token: str,
        login_customer_id: str | None = None,
    ) -> list[dict[str, object]]:
        self.campaign_calls += 1
        return [
            {"campaign": {"id": "cmp_1", "name": "Search US", "status": "ENABLED"}},
            {"campaign": {"id": "cmp_2", "name": "Display Retargeting", "status": "PAUSED"}},
        ]

    async def get_customer_metrics(
        self,
        *,
        customer_id: str,
        access_token: str,
        since: str,
        until: str,
        login_customer_id: str | None = None,
    ) -> dict[str, object]:
        self.summary_calls += 1
        if since == "2026-05-17":
            return {
                "metrics": {
                    "costMicros": "180000000",
                    "impressions": "16000",
                    "clicks": "320",
                    "conversions": "18",
                }
            }
        return {
            "metrics": {
                "costMicros": "120000000",
                "impressions": "12000",
                "clicks": "240",
                "conversions": "12",
            }
        }

    async def get_campaign_metrics(
        self,
        *,
        customer_id: str,
        access_token: str,
        since: str,
        until: str,
        login_customer_id: str | None = None,
    ) -> list[dict[str, object]]:
        self.campaign_metric_calls += 1
        if since == "2026-05-17":
            return [
                {
                    "campaign": {"id": "cmp_1"},
                    "metrics": {
                        "costMicros": "150000000",
                        "impressions": "12000",
                        "clicks": "260",
                        "conversions": "15",
                    },
                },
                {
                    "campaign": {"id": "cmp_2"},
                    "metrics": {
                        "costMicros": "30000000",
                        "impressions": "4000",
                        "clicks": "60",
                        "conversions": "3",
                    },
                },
            ]
        return [
            {
                "campaign": {"id": "cmp_1"},
                "metrics": {
                    "costMicros": "100000000",
                    "impressions": "9000",
                    "clicks": "200",
                    "conversions": "10",
                },
            },
            {
                "campaign": {"id": "cmp_2"},
                "metrics": {
                    "costMicros": "20000000",
                    "impressions": "3000",
                    "clicks": "40",
                    "conversions": "2",
                },
            },
        ]

    async def get_ad_metrics(
        self,
        *,
        customer_id: str,
        access_token: str,
        since: str,
        until: str,
        login_customer_id: str | None = None,
    ) -> list[dict[str, object]]:
        self.ad_metric_calls += 1
        return [
            {
                "campaign": {"id": "cmp_1"},
                "adGroupAd": {"ad": {"id": "ad_1", "type": "RESPONSIVE_SEARCH_AD"}},
                "metrics": {
                    "costMicros": "60000000",
                    "impressions": "6000",
                    "clicks": "120",
                    "conversions": "7",
                },
            },
            {
                "campaign": {"id": "cmp_1"},
                "adGroupAd": {"ad": {"id": "ad_2", "type": "RESPONSIVE_SEARCH_AD"}},
                "metrics": {
                    "costMicros": "40000000",
                    "impressions": "3000",
                    "clicks": "80",
                    "conversions": "3",
                },
            },
            {
                "campaign": {"id": "cmp_2"},
                "adGroupAd": {"ad": {"id": "ad_3", "type": "IMAGE_AD"}},
                "metrics": {
                    "costMicros": "20000000",
                    "impressions": "3000",
                    "clicks": "40",
                    "conversions": "2",
                },
            },
        ]


@pytest.mark.unit
@pytest.mark.service
async def test_generate_google_ads_report_use_case_builds_dashboard_payload(db_session):
    encryption_service = EncryptionService()
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="en"))
    db_session.add(
        GoogleAdsConnection(
            id="google-conn-1",
            user_id="user-1",
            refresh_token_encrypted=encryption_service.encrypt("google-refresh-token"),
            access_token_encrypted=encryption_service.encrypt("stale-access-token"),
            scopes="https://www.googleapis.com/auth/adwords",
        )
    )
    db_session.add(
        GoogleAdsCustomer(
            id="google-customer-1",
            connection_id="google-conn-1",
            external_customer_id="1234567890",
            resource_name="customers/1234567890",
            descriptive_name="Stored customer",
            currency_code="USD",
            time_zone="America/New_York",
            is_manager=False,
            is_directly_accessible=False,
            hierarchy_level=1,
            root_customer_id="9988776655",
            manager_customer_id="9988776655",
            login_customer_id="9988776655",
        )
    )
    await db_session.commit()

    fake_client = FakeGoogleAdsReportClient()
    use_case = GenerateGoogleAdsReportUseCase(
        session=db_session,
        date_range_service=FixedDateRangeService(),
        report_service=GoogleAdsReportService(
            google_ads_client=fake_client,
            encryption_service=encryption_service,
        ),
    )

    report = await use_case.execute(user_id="user-1", customer_id="1234567890", days=30)

    assert report["account"]["name"] == "Google Main Account"
    assert report["summary"]["active_campaigns"] == 1
    assert report["summary"]["metrics"]["spend"]["current"] == 180.0
    assert report["summary"]["metrics"]["reach"]["current"] is None
    assert report["summary"]["metrics"]["results"]["current"] == 18.0
    assert report["campaigns"][0]["name"] == "Search US"
    assert report["campaigns"][0]["metrics"]["cpc"]["current"] == 150.0 / 260.0
    assert report["campaigns"][0]["creatives"][0]["name"] == "Responsive Search Ad #ad_1"
    assert report["campaigns"][0]["creatives"][0]["metrics"]["ctr"] == 2.0
    assert report["campaigns"][1]["creatives"][0]["object_type"] == "IMAGE_AD"

    async with db_helper.session_factory() as verification_session:
        stored_customer = await verification_session.get(GoogleAdsCustomer, "google-customer-1")
        stored_connection = await verification_session.get(GoogleAdsConnection, "google-conn-1")
        assert stored_customer is not None
        assert stored_customer.last_synced_at is not None
        assert stored_connection is not None
        assert encryption_service.decrypt(stored_connection.access_token_encrypted) == "google-access-token"

    context = build_report_context(report)
    assert "acct|Google Main Account|1234567890|USD|America/New_York" in context
    assert "sum|result|1|2|sp:180,120,50" in context
    assert "cmp|Search US|ENABLED|result|" in context
    assert "crt|Responsive Search Ad #ad_1|RESPONSIVE_SEARCH_AD|60|6000|120|2|7|result" in context

    assert fake_client.refresh_calls == 1
    assert fake_client.customer_calls == 1
    assert fake_client.campaign_calls == 1
    assert fake_client.summary_calls == 2
    assert fake_client.campaign_metric_calls == 2
    assert fake_client.ad_metric_calls == 1
