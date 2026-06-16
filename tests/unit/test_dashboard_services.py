from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.models.meta_ad_account import MetaAdAccount
from core.models.meta_connection import MetaConnection
from core.models.user import User
from core.security.encryption_service import EncryptionService
from core.services.date_range_service import DateRangeService
from core.services.meta_report_service import MetaReportService
from core.use_cases.dashboard import GenerateMetaReportUseCase
from core.utils.ai_context import build_report_context
from core.utils.reporting import extract_primary_result, group_ads_by_campaign, percentage_delta


class FakeMetaReportClient:
    async def get_ad_account(self, *, account_id: str, access_token: str) -> dict[str, object]:
        assert account_id == "act_1"
        assert access_token == "meta-token"
        return {
            "id": "act_1",
            "account_id": "111",
            "name": "Main account",
            "currency": "USD",
            "timezone_name": "Asia/Almaty",
        }

    async def list_campaigns(self, *, account_id: str, access_token: str) -> list[dict[str, object]]:
        return [
            {"id": "cmp_1", "name": "Lead Gen", "effective_status": "ACTIVE"},
            {"id": "cmp_2", "name": "Remarketing", "effective_status": "PAUSED"},
        ]

    async def get_account_insights(self, *, account_id: str, access_token: str, since: str, until: str):
        if since == "2026-05-17":
            return {
                "spend": "150.0",
                "impressions": "12000",
                "clicks": "300",
                "reach": "9000",
                "cpm": "12.5",
                "ctr": "2.5",
                "actions": [{"action_type": "lead", "value": "15"}],
            }
        return {
            "spend": "120.0",
            "impressions": "10000",
            "clicks": "250",
            "reach": "7500",
            "cpm": "12.0",
            "ctr": "2.3",
            "actions": [{"action_type": "lead", "value": "12"}],
        }

    async def get_campaign_insights(self, *, account_id: str, access_token: str, since: str, until: str):
        if since == "2026-05-17":
            return [
                {
                    "campaign_id": "cmp_1",
                    "spend": "120.0",
                    "impressions": "9000",
                    "clicks": "220",
                    "reach": "7000",
                    "cpm": "13.0",
                    "ctr": "2.4",
                    "actions": [{"action_type": "lead", "value": "12"}],
                },
                {
                    "campaign_id": "cmp_2",
                    "spend": "30.0",
                    "impressions": "3000",
                    "clicks": "80",
                    "reach": "2000",
                    "cpm": "10.0",
                    "ctr": "2.6",
                    "actions": [{"action_type": "lead", "value": "3"}],
                },
            ]
        return [
            {
                "campaign_id": "cmp_1",
                "spend": "100.0",
                "impressions": "8000",
                "clicks": "200",
                "reach": "6500",
                "cpm": "12.5",
                "ctr": "2.5",
                "actions": [{"action_type": "lead", "value": "10"}],
            },
            {
                "campaign_id": "cmp_2",
                "spend": "20.0",
                "impressions": "2000",
                "clicks": "50",
                "reach": "1000",
                "cpm": "10.0",
                "ctr": "2.5",
                "actions": [{"action_type": "lead", "value": "2"}],
            },
        ]

    async def list_ads(self, *, account_id: str, access_token: str) -> list[dict[str, object]]:
        return [
            {
                "id": "ad_1",
                "name": "Creative A",
                "campaign_id": "cmp_1",
                "creative": {
                    "object_type": "IMAGE",
                    "thumbnail_url": "https://cdn.test/creative-a.jpg",
                    "image_url": "https://cdn.test/creative-a.jpg",
                },
            },
            {
                "id": "ad_2",
                "name": "Creative B",
                "campaign_id": "cmp_1",
                "creative": {
                    "object_type": "VIDEO",
                    "thumbnail_url": "https://cdn.test/creative-b.jpg",
                    "image_url": None,
                },
            },
        ]

    async def get_ad_insights(self, *, account_id: str, access_token: str, since: str, until: str) -> list[dict[str, object]]:
        return [
            {
                "ad_id": "ad_1",
                "spend": "70.0",
                "impressions": "5000",
                "clicks": "150",
                "ctr": "3.0",
                "actions": [{"action_type": "lead", "value": "8"}],
            },
            {
                "ad_id": "ad_2",
                "spend": "50.0",
                "impressions": "4000",
                "clicks": "70",
                "ctr": "1.75",
                "actions": [{"action_type": "lead", "value": "4"}],
            },
        ]


class FixedDateRangeService:
    def build_periods(self, *, days: int, now=None):
        return DateRangeService().build_periods(days=days, now=datetime(2026, 6, 15, tzinfo=timezone.utc))


@pytest.mark.unit
@pytest.mark.service
async def test_generate_meta_report_use_case_builds_sorted_dashboard_payload(db_session):
    encryption_service = EncryptionService()
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="kz"))
    db_session.add(
        MetaConnection(
            id="conn-1",
            user_id="user-1",
            meta_user_id="meta-user-1",
            meta_user_name="Meta Owner",
            access_token_encrypted=encryption_service.encrypt("meta-token"),
            scopes="ads_read",
        )
    )
    db_session.add(
        MetaAdAccount(
            id="acc-1",
            connection_id="conn-1",
            external_id="act_1",
            account_id="111",
            name="Main account",
            currency="USD",
            timezone_name="Asia/Almaty",
            account_status=1,
        )
    )
    await db_session.commit()

    use_case = GenerateMetaReportUseCase(
        session=db_session,
        date_range_service=FixedDateRangeService(),
        report_service=MetaReportService(
            meta_client=FakeMetaReportClient(),
            encryption_service=encryption_service,
        ),
    )

    report = await use_case.execute(user_id="user-1", ad_account_id="act_1", days=30)

    assert report["summary"]["active_campaigns"] == 1
    assert report["summary"]["metrics"]["spend"]["current"] == 150.0
    assert report["summary"]["metrics"]["results"]["current"] == 15
    assert report["campaigns"][0]["name"] == "Lead Gen"
    assert report["campaigns"][0]["creatives"][0]["name"] == "Creative A"
    assert report["campaigns"][0]["metrics"]["cost_per_result"]["current"] == 10.0

    context = build_report_context(report)
    assert "Main account" in context
    assert "Creative A" in context


@pytest.mark.unit
@pytest.mark.service
def test_reporting_helpers():
    periods = DateRangeService().build_periods(days=30, now=datetime(2026, 6, 15, tzinfo=timezone.utc))
    assert periods["current"] == {"since": "2026-05-17", "until": "2026-06-15"}
    assert periods["previous"] == {"since": "2026-04-17", "until": "2026-05-16"}

    result_kind, result_value = extract_primary_result([{"action_type": "lead", "value": "7"}])
    assert (result_kind, result_value) == ("leads", 7)
    assert percentage_delta(120, 100) == 20.0
    assert group_ads_by_campaign([{"id": "1", "campaign_id": "cmp"}, {"id": "2"}]) == {
        "cmp": [{"id": "1", "campaign_id": "cmp"}]
    }
