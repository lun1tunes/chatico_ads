from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from api_v1.ai.schemas import AutoVerdictRequest
from api_v1.ai import views as ai_views
from core.services.ai_prompt_service import PromptBundle


def _sample_report() -> dict[str, object]:
    return {
        "account": {"name": "Main account", "account_id": "123", "currency": "USD", "timezone_name": "Asia/Almaty"},
        "periods": {"current": {"since": "2026-06-01", "until": "2026-06-30"}},
        "summary": {
            "active_campaigns": 1,
            "metrics": {
                "spend": {"current": 120.0},
                "impressions": {"current": 1500},
                "clicks": {"current": 120},
                "results": {"current": 10},
            },
        },
        "campaigns": [],
    }


@pytest.mark.unit
@pytest.mark.api
async def test_auto_verdict_keeps_request_scope_immutable_when_effective_scope_changes(monkeypatch):
    payload = AutoVerdictRequest(language="en", scope="campaign", campaign_id="cmp-1")
    report = _sample_report()
    user = SimpleNamespace(id="user-1")
    container = SimpleNamespace(
        generate_meta_report_use_case=Mock(return_value=SimpleNamespace(execute=AsyncMock(return_value=report))),
    )

    scoped_context_call: dict[str, object] = {}
    prompt_bundle_call: dict[str, object] = {}

    def fake_build_scoped_report_context(report_data, *, scope, campaign_id, ad_group_id, creative_id):
        scoped_context_call["scope"] = scope
        scoped_context_call["campaign_id"] = campaign_id
        scoped_context_call["ad_group_id"] = ad_group_id
        scoped_context_call["creative_id"] = creative_id
        return "scope|account|123|Main account", "account", report_data

    def fake_build_auto_verdict_prompt_bundle(*, scope, **kwargs):
        prompt_bundle_call["scope"] = scope
        return PromptBundle(system_prompt="system", messages=[{"role": "user", "content": "dashboard context"}], checksums={})

    monkeypatch.setattr(ai_views, "build_scoped_report_context", fake_build_scoped_report_context)
    monkeypatch.setattr(ai_views, "_build_auto_verdict_prompt_bundle", fake_build_auto_verdict_prompt_bundle)
    monkeypatch.setattr(
        ai_views,
        "_generate_auto_verdict_text",
        AsyncMock(
            return_value=(
                "Performance is stable overall. Spend, clicks, and results remain healthy, "
                "so keep scaling carefully while watching cost per result."
            )
        ),
    )
    monkeypatch.setattr(ai_views, "_auto_verdict_response_text", lambda *, text, report, payload: text)

    response = await ai_views.auto_verdict(
        "act_1",
        payload,
        user=user,
        session=None,
        container=container,
    )

    assert response.text.startswith("Performance is stable overall.")
    assert payload.scope == "campaign"
    assert scoped_context_call == {
        "scope": "campaign",
        "campaign_id": "cmp-1",
        "ad_group_id": None,
        "creative_id": None,
    }
    assert prompt_bundle_call["scope"] == "account"

