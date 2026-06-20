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
    def __init__(self) -> None:
        self.account_info_calls = 0
        self.campaign_list_calls = 0
        self.account_insight_calls = 0
        self.campaign_insight_calls = 0
        self.ads_calls = 0
        self.ad_insight_calls = 0

    async def get_ad_account(self, *, account_id: str, access_token: str) -> dict[str, object]:
        self.account_info_calls += 1
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
        self.campaign_list_calls += 1
        return [
            {"id": "cmp_1", "name": "Lead Gen", "effective_status": "ACTIVE"},
            {"id": "cmp_2", "name": "Remarketing", "effective_status": "PAUSED"},
        ]

    async def get_account_insights(self, *, account_id: str, access_token: str, since: str, until: str):
        self.account_insight_calls += 1
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
        self.campaign_insight_calls += 1
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
        self.ads_calls += 1
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
                    "object_story_spec": {
                        "video_data": {
                            "image_url": "https://cdn.test/creative-b-hq.jpg",
                        }
                    },
                },
            },
            {
                "id": "ad_3",
                "name": "Creative Share",
                "campaign_id": "cmp_2",
                "creative": {
                    "object_type": "SHARE",
                    "thumbnail_url": "https://cdn.test/creative-share-thumb.jpg",
                    "image_url": None,
                    "object_story_spec": {
                        "link_data": {
                            "picture": "https://cdn.test/creative-share-hq.jpg",
                        }
                    },
                },
            },
            {
                "id": "ad_4",
                "name": "Пока вы занимаетесь",
                "campaign_id": "cmp_1",
                "creative": {
                    "object_type": "VIDEO",
                    "thumbnail_url": (
                        "https://cdn.test/creative-low.jpg?stp=c0.5000x0.5000f_dst-emg0_p64x64_q75_tt6"
                    ),
                    "image_url": None,
                    "instagram_permalink_url": "https://www.instagram.com/p/test-low-res/",
                },
            },
        ]

    async def get_ad_insights(self, *, account_id: str, access_token: str, since: str, until: str) -> list[dict[str, object]]:
        self.ad_insight_calls += 1
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
            {
                "ad_id": "ad_3",
                "spend": "20.0",
                "impressions": "1500",
                "clicks": "35",
                "ctr": "2.33",
                "actions": [{"action_type": "lead", "value": "2"}],
            },
            {
                "ad_id": "ad_4",
                "spend": "40.0",
                "impressions": "2200",
                "clicks": "42",
                "ctr": "1.91",
                "actions": [{"action_type": "lead", "value": "3"}],
            },
        ]


class FixedDateRangeService:
    def build_periods(self, *, days: int, now=None):
        return DateRangeService().build_periods(days=days, now=datetime(2026, 6, 15, tzinfo=timezone.utc))


class FakePreviewClient:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def resolve_instagram_permalink_preview(self, *, permalink_url: str) -> str | None:
        self.calls.append(permalink_url)
        if permalink_url == "https://www.instagram.com/p/test-low-res/":
            return "https://cdninstagram.test/creative-low-hq.jpg"
        return None


@pytest.mark.unit
@pytest.mark.service
async def test_generate_meta_report_use_case_builds_sorted_dashboard_payload(db_session):
    encryption_service = EncryptionService()
    preview_client = FakePreviewClient()
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
            preview_client=preview_client,
        ),
    )

    report = await use_case.execute(user_id="user-1", ad_account_id="act_1", days=30)

    assert report["summary"]["active_campaigns"] == 1
    assert report["summary"]["metrics"]["spend"]["current"] == 150.0
    assert report["summary"]["metrics"]["results"]["current"] == 15
    assert report["campaigns"][0]["name"] == "Lead Gen"
    assert report["campaigns"][0]["creatives"][0]["name"] == "Creative A"
    assert report["campaigns"][0]["creatives"][1]["image_url"] == "https://cdn.test/creative-b-hq.jpg"
    low_res_creative = next(
        creative for creative in report["campaigns"][0]["creatives"] if creative["name"] == "Пока вы занимаетесь"
    )
    assert low_res_creative["image_url"] == "https://cdninstagram.test/creative-low-hq.jpg"
    assert report["campaigns"][1]["creatives"][0]["image_url"] == "https://cdn.test/creative-share-hq.jpg"
    assert report["campaigns"][0]["metrics"]["cost_per_result"]["current"] == 10.0
    assert preview_client.calls == ["https://www.instagram.com/p/test-low-res/"]

    context = build_report_context(report)
    assert "acct|Main account|111|USD|Asia/Almaty" in context
    assert "sum|leads|1|2|sp:150,120,25" in context
    assert "crt|Creative A|IMAGE|70|5000|150|3|8|leads" in context
    assert "crt|Пока вы занимаетесь|VIDEO|40|2200|42|1.91|3|leads" in context
    assert "https://cdn.test/creative-a.jpg" not in context


@pytest.mark.unit
@pytest.mark.service
async def test_generate_meta_report_use_case_reuses_cached_payload_and_supports_force_refresh(db_session):
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

    fake_client = FakeMetaReportClient()
    preview_client = FakePreviewClient()
    use_case = GenerateMetaReportUseCase(
        session=db_session,
        date_range_service=FixedDateRangeService(),
        report_service=MetaReportService(
            meta_client=fake_client,
            encryption_service=encryption_service,
            preview_client=preview_client,
            cache_ttl_seconds=60,
        ),
    )

    first_report = await use_case.execute(user_id="user-1", ad_account_id="act_1", days=30)
    second_report = await use_case.execute(user_id="user-1", ad_account_id="act_1", days=30)
    refreshed_report = await use_case.execute(user_id="user-1", ad_account_id="act_1", days=30, force_refresh=True)

    assert first_report["summary"]["metrics"]["spend"]["current"] == 150.0
    assert second_report == first_report
    assert refreshed_report == first_report
    assert fake_client.account_info_calls == 2
    assert fake_client.campaign_list_calls == 2
    assert fake_client.account_insight_calls == 4
    assert fake_client.campaign_insight_calls == 4
    assert fake_client.ads_calls == 2
    assert fake_client.ad_insight_calls == 2
    assert preview_client.calls == [
        "https://www.instagram.com/p/test-low-res/",
        "https://www.instagram.com/p/test-low-res/",
    ]


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


@pytest.mark.unit
@pytest.mark.service
def test_build_report_context_sanitizes_delimiters_and_limits_campaigns_and_creatives():
    report = {
        "account": {"name": "Main|Account", "account_id": "111", "currency": "USD", "timezone_name": "Asia/Almaty"},
        "periods": {
            "current": {"since": "2026-05-17", "until": "2026-06-15"},
            "previous": {"since": "2026-04-17", "until": "2026-05-16"},
        },
        "summary": {
            "primary_result_kind": "leads",
            "active_campaigns": 13,
            "total_campaigns": 13,
            "metrics": {
                "spend": {"current": 150.0, "previous": 120.0, "delta_pct": 25.0},
                "reach": {"current": 1000, "previous": 900, "delta_pct": 11.1},
                "impressions": {"current": 1500, "previous": 1400, "delta_pct": 7.1},
                "clicks": {"current": 120, "previous": 100, "delta_pct": 20.0},
                "ctr": {"current": 8.0, "previous": 7.0, "delta_pct": 14.3},
                "cpm": {"current": 10.0, "previous": 9.0, "delta_pct": 11.1},
                "cpc": {"current": 1.0, "previous": 1.0, "delta_pct": 0.0},
                "results": {"current": 10, "previous": 8, "delta_pct": 25.0},
                "cost_per_result": {"current": 12.0, "previous": 12.5, "delta_pct": -4.0},
            },
        },
        "campaigns": [
            {
                "name": f"Campaign {index}|Name",
                "status": "ACTIVE",
                "primary_result_kind": "leads",
                "metrics": {
                    "spend": {"current": float(100 - index), "previous": 50.0, "delta_pct": 10.0},
                    "reach": {"current": 1000, "previous": 900, "delta_pct": 11.1},
                    "impressions": {"current": 1500, "previous": 1400, "delta_pct": 7.1},
                    "clicks": {"current": 120, "previous": 100, "delta_pct": 20.0},
                    "ctr": {"current": 8.0, "previous": 7.0, "delta_pct": 14.3},
                    "cpm": {"current": 10.0, "previous": 9.0, "delta_pct": 11.1},
                    "cpc": {"current": 1.0, "previous": 1.0, "delta_pct": 0.0},
                    "results": {"current": 10 - index, "previous": 8, "delta_pct": 25.0},
                    "cost_per_result": {"current": 12.0, "previous": 12.5, "delta_pct": -4.0},
                },
                "creatives": [
                    {
                        "name": f"Creative {creative_index};variant",
                        "object_type": "VIDEO",
                        "metrics": {
                            "spend": float(20 - creative_index),
                            "impressions": 1000 + creative_index,
                            "clicks": 50 + creative_index,
                            "ctr": 2.5,
                            "results": 5 - min(creative_index, 4),
                            "result_kind": "leads",
                        },
                    }
                    for creative_index in range(8)
                ],
            }
            for index in range(13)
        ],
    }

    context = build_report_context(report)

    assert "Main|Account" not in context
    assert "Campaign 0|Name" not in context
    assert "Creative 0;variant" not in context
    assert "acct|Main / Account|111|USD|Asia/Almaty" in context
    assert context.count("\ncmp|") == 12
    assert "more|cmp|1" in context
    assert "more|crt|Campaign 0 / Name|2" in context
