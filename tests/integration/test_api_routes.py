from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from core.dependencies import get_current_user, get_db_session, get_di_container
from core.infrastructure.llm_clients import LLMProxyError
from core.infrastructure.meta_graph_api import MetaGraphAPIError
from core.services.meta_report_service import MetaAdAccountNotFoundError
from main import app


async def _override_current_user():
    return SimpleNamespace(id="user-1", email="owner@example.com", locale="kz", is_active=True)


async def _override_db_session():
    yield None


class FakeContainer:
    def __init__(self) -> None:
        self.build_meta_oauth_url_use_case = Mock()
        self.handle_meta_oauth_callback_use_case = Mock()
        self.list_meta_ad_accounts_use_case = Mock()
        self.generate_meta_report_use_case = Mock()
        self.generate_auto_verdict_use_case = Mock()
        self.ask_dashboard_use_case = Mock()


@pytest.mark.integration
@pytest.mark.api
async def test_health_endpoints(async_client):
    live_response = await async_client.get("/health/live")
    ready_response = await async_client.get("/health/ready")

    assert live_response.status_code == 200
    assert live_response.json() == {"status": "ok"}
    assert ready_response.status_code == 200
    assert ready_response.json() == {"status": "ok"}


@pytest.mark.integration
@pytest.mark.api
async def test_meta_routes(async_client):
    container = FakeContainer()
    container.build_meta_oauth_url_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(return_value={"authorization_url": "https://facebook.test/oauth"}),
    )
    container.handle_meta_oauth_callback_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(return_value={"user_id": "user-1", "connection_id": "conn-1"}),
    )
    container.list_meta_ad_accounts_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id="acc-1",
                    external_id="act_1",
                    account_id="123",
                    name="Main account",
                    currency="USD",
                    timezone_name="Asia/Almaty",
                    account_status=1,
                )
            ]
        ),
    )

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_di_container] = lambda: container

    start_response = await async_client.get("/api/v1/meta/oauth/start")
    assert start_response.status_code == 200
    assert start_response.json()["authorization_url"] == "https://facebook.test/oauth"

    callback_response = await async_client.get(
        "/api/v1/meta/oauth/callback?code=test-code&state=test-state",
        follow_redirects=False,
    )
    assert callback_response.status_code == 307
    assert callback_response.headers["location"].endswith("/connections?provider=meta&status=success")

    accounts_response = await async_client.get("/api/v1/meta/ad-accounts")
    assert accounts_response.status_code == 200
    assert accounts_response.json()[0]["external_id"] == "act_1"


@pytest.mark.integration
@pytest.mark.api
async def test_dashboard_and_ai_routes_map_errors(async_client):
    container = FakeContainer()
    container.generate_meta_report_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(side_effect=MetaAdAccountNotFoundError("Meta ad account not found")),
    )
    container.generate_auto_verdict_use_case.return_value = SimpleNamespace(execute=AsyncMock(return_value="ok"))
    container.ask_dashboard_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(side_effect=LLMProxyError("Unsupported AI provider")),
    )

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_di_container] = lambda: container

    report_response = await async_client.get("/api/v1/dashboard/meta/ad-accounts/act_1/report")
    assert report_response.status_code == 404
    assert report_response.json()["detail"] == "Meta ad account not found"

    auto_verdict_response = await async_client.post(
        "/api/v1/ai/meta/ad-accounts/act_1/auto-verdict",
        json={"days": 30, "language": "kz"},
    )
    assert auto_verdict_response.status_code == 404

    container.generate_meta_report_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(
            return_value={
                "account": {"name": "Main account", "account_id": "123"},
                "periods": {
                    "current": {"since": "2026-06-01", "until": "2026-06-30"},
                    "previous": {"since": "2026-05-01", "until": "2026-05-31"},
                },
                "summary": {
                    "primary_result_kind": "leads",
                    "metrics": {
                        "spend": {"current": 120.0, "previous": 100.0, "delta_pct": 20.0},
                        "reach": {"current": 1000, "previous": 900, "delta_pct": 11.1},
                        "impressions": {"current": 1500, "previous": 1400, "delta_pct": 7.1},
                        "clicks": {"current": 120, "previous": 100, "delta_pct": 20.0},
                        "ctr": {"current": 8.0, "previous": 7.0, "delta_pct": 14.3},
                        "cpm": {"current": 10.0, "previous": 9.0, "delta_pct": 11.1},
                        "cpc": {"current": 1.0, "previous": 1.0, "delta_pct": 0.0},
                        "results": {"current": 10, "previous": 8, "delta_pct": 25.0},
                        "cost_per_result": {"current": 12.0, "previous": 12.5, "delta_pct": -4.0},
                    },
                    "active_campaigns": 1,
                    "total_campaigns": 1,
                },
                "campaigns": [],
            }
        ),
    )

    chat_response = await async_client.post(
        "/api/v1/ai/meta/ad-accounts/act_1/chat",
        json={
            "days": 30,
            "language": "kz",
            "provider": "unsupported",
            "api_key": "1234567890-client-key",
            "messages": [{"role": "user", "content": "test"}],
        },
    )
    assert chat_response.status_code == 400
    assert chat_response.json()["detail"] == "Unsupported AI provider"


@pytest.mark.integration
@pytest.mark.api
async def test_dashboard_route_maps_meta_upstream_error(async_client):
    container = FakeContainer()
    container.generate_meta_report_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(side_effect=MetaGraphAPIError("Meta upstream failed")),
    )

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_di_container] = lambda: container

    response = await async_client.get("/api/v1/dashboard/meta/ad-accounts/act_1/report")
    assert response.status_code == 502
    assert response.json()["detail"] == "Meta upstream failed"
