from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from core.dependencies import get_current_user, get_db_session, get_di_container
from core.infrastructure.google_ads_api import GoogleAdsConfigurationError
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
        self.build_google_ads_oauth_url_use_case = Mock()
        self.handle_google_ads_oauth_callback_use_case = Mock()
        self.list_google_ads_customers_use_case = Mock()
        self.generate_meta_report_use_case = Mock()
        self.generate_auto_verdict_use_case = Mock()
        self.list_supported_ai_providers_use_case = Mock()
        self.list_saved_ai_provider_keys_use_case = Mock()
        self.save_ai_provider_key_use_case = Mock()
        self.delete_ai_provider_key_use_case = Mock()
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
async def test_google_ads_routes(async_client):
    container = FakeContainer()
    container.build_google_ads_oauth_url_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(return_value={"authorization_url": "https://accounts.google.test/o/oauth2/v2/auth"}),
    )
    container.handle_google_ads_oauth_callback_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(return_value={"user_id": "user-1", "connection_id": "google-conn-1", "customer_count": 2}),
    )
    container.list_google_ads_customers_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(
            return_value=[
                SimpleNamespace(
                    id="google-customer-1",
                    external_customer_id="1234567890",
                    resource_name="customers/1234567890",
                    descriptive_name="Primary MCC",
                    currency_code="USD",
                    time_zone="Europe/Paris",
                    is_manager=True,
                    is_directly_accessible=True,
                    hierarchy_level=0,
                    root_customer_id="1234567890",
                    manager_customer_id=None,
                    login_customer_id=None,
                )
            ]
        ),
    )

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_di_container] = lambda: container

    start_response = await async_client.get("/api/v1/google-ads/oauth/start")
    assert start_response.status_code == 200
    assert start_response.json()["authorization_url"] == "https://accounts.google.test/o/oauth2/v2/auth"

    callback_response = await async_client.get(
        "/api/v1/google-ads/oauth/callback?code=test-code&state=test-state",
        follow_redirects=False,
    )
    assert callback_response.status_code == 307
    assert callback_response.headers["location"].endswith("/connections?provider=google_ads&status=success")

    customers_response = await async_client.get("/api/v1/google-ads/customers")
    assert customers_response.status_code == 200
    assert customers_response.json()[0]["external_customer_id"] == "1234567890"


@pytest.mark.integration
@pytest.mark.api
async def test_google_ads_oauth_routes_handle_configuration_and_callback_errors(async_client):
    container = FakeContainer()
    container.build_google_ads_oauth_url_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(side_effect=GoogleAdsConfigurationError("Google Ads OAuth is not configured")),
    )

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_di_container] = lambda: container

    start_response = await async_client.get("/api/v1/google-ads/oauth/start")
    assert start_response.status_code == 503
    assert start_response.json()["detail"] == "Google Ads OAuth is not configured"

    denied_response = await async_client.get(
        "/api/v1/google-ads/oauth/callback?error=access_denied&error_description=User%20denied%20access",
        follow_redirects=False,
    )
    assert denied_response.status_code == 307
    assert "provider=google_ads" in denied_response.headers["location"]
    assert "status=error" in denied_response.headers["location"]
    assert "User+denied+access" in denied_response.headers["location"]

    missing_params_response = await async_client.get(
        "/api/v1/google-ads/oauth/callback",
        follow_redirects=False,
    )
    assert missing_params_response.status_code == 307
    assert "Missing+Google+OAuth+callback+parameters" in missing_params_response.headers["location"]

    container.handle_google_ads_oauth_callback_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(side_effect=RuntimeError("low-level boom")),
    )

    callback_error_response = await async_client.get(
        "/api/v1/google-ads/oauth/callback?code=test-code&state=test-state",
        follow_redirects=False,
    )
    assert callback_error_response.status_code == 307
    assert "provider=google_ads" in callback_error_response.headers["location"]
    assert "Google+Ads+connection+failed.+Please+try+again." in callback_error_response.headers["location"]


@pytest.mark.integration
@pytest.mark.api
async def test_meta_oauth_callback_handles_denied_access(async_client):
    container = FakeContainer()

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_di_container] = lambda: container

    denied_response = await async_client.get(
        "/api/v1/meta/oauth/callback?error=access_denied&error_description=User%20denied%20access",
        follow_redirects=False,
    )
    assert denied_response.status_code == 307
    assert "provider=meta" in denied_response.headers["location"]
    assert "status=error" in denied_response.headers["location"]
    assert "User+denied+access" in denied_response.headers["location"]


@pytest.mark.integration
@pytest.mark.api
async def test_dashboard_and_ai_routes_map_errors(async_client):
    container = FakeContainer()
    container.list_supported_ai_providers_use_case.return_value = SimpleNamespace(
        execute=Mock(
            return_value=[
                {
                    "key": "gemini",
                    "label": "Gemini",
                    "default_model": "gemini-3.5-flash",
                    "presets": [
                        {
                            "value": "gemini-3.5-flash",
                            "label": "gemini-3.5-flash",
                            "is_default": True,
                        }
                    ],
                    "supports_custom_model": True,
                }
            ]
        )
    )
    container.generate_meta_report_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(side_effect=MetaAdAccountNotFoundError("Meta ad account not found")),
    )
    container.generate_auto_verdict_use_case.return_value = SimpleNamespace(execute=AsyncMock(return_value="ok"))
    container.list_saved_ai_provider_keys_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(
            return_value=[{"provider": "gemini", "has_saved_key": True, "updated_at": "2026-06-18T07:20:00"}]
        ),
    )
    container.save_ai_provider_key_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(
            return_value={"provider": "gemini", "has_saved_key": True, "updated_at": "2026-06-18T07:21:00"}
        ),
    )
    container.delete_ai_provider_key_use_case.return_value = SimpleNamespace(execute=AsyncMock(return_value=None))
    container.ask_dashboard_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(side_effect=LLMProxyError("Unsupported AI provider")),
    )

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_di_container] = lambda: container

    report_response = await async_client.get("/api/v1/dashboard/meta/ad-accounts/act_1/report")
    assert report_response.status_code == 404
    assert report_response.json()["detail"] == "Meta ad account not found"

    providers_response = await async_client.get("/api/v1/ai/providers")
    assert providers_response.status_code == 200
    assert providers_response.json()[0]["default_model"] == "gemini-3.5-flash"

    provider_keys_response = await async_client.get("/api/v1/ai/provider-keys")
    assert provider_keys_response.status_code == 200
    assert provider_keys_response.json()[0]["provider"] == "gemini"

    save_provider_key_response = await async_client.put(
        "/api/v1/ai/provider-keys/gemini",
        json={"api_key": "1234567890-client-key"},
    )
    assert save_provider_key_response.status_code == 200
    assert save_provider_key_response.json()["provider"] == "gemini"

    delete_provider_key_response = await async_client.delete("/api/v1/ai/provider-keys/gemini")
    assert delete_provider_key_response.status_code == 204

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
    container.ask_dashboard_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(return_value="internal-chat-ok"),
    )

    default_chat_response = await async_client.post(
        "/api/v1/ai/meta/ad-accounts/act_1/chat",
        json={
            "days": 30,
            "language": "kz",
            "messages": [{"role": "user", "content": "test"}],
        },
    )
    assert default_chat_response.status_code == 200
    assert default_chat_response.json()["text"] == "internal-chat-ok"
    default_chat_call = container.ask_dashboard_use_case.return_value.execute.await_args_list[0].kwargs
    assert default_chat_call["use_client_credentials"] is False
    assert default_chat_call["provider"] is None

    container.ask_dashboard_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(side_effect=LLMProxyError("Unsupported AI provider")),
    )

    chat_response = await async_client.post(
        "/api/v1/ai/meta/ad-accounts/act_1/chat",
        json={
            "days": 30,
            "language": "kz",
            "use_client_credentials": True,
            "provider": "unsupported",
            "api_key": "1234567890-client-key",
            "messages": [{"role": "user", "content": "test"}],
        },
    )
    assert chat_response.status_code == 400
    assert chat_response.json()["detail"] == "Unsupported AI provider"

    container.ask_dashboard_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(side_effect=LLMProxyError("The last chat message must come from the user")),
    )

    invalid_chat_shape_response = await async_client.post(
        "/api/v1/ai/meta/ad-accounts/act_1/chat",
        json={
            "days": 30,
            "language": "kz",
            "use_client_credentials": True,
            "provider": "anthropic",
            "api_key": "1234567890-client-key",
            "messages": [{"role": "assistant", "content": "prefill"}],
        },
    )
    assert invalid_chat_shape_response.status_code == 400
    assert invalid_chat_shape_response.json()["detail"] == "The last chat message must come from the user"

    container.ask_dashboard_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(side_effect=LLMProxyError("Add an API key or save one for this provider")),
    )

    missing_provider_key_response = await async_client.post(
        "/api/v1/ai/meta/ad-accounts/act_1/chat",
        json={
            "days": 30,
            "language": "kz",
            "use_client_credentials": True,
            "provider": "gemini",
            "messages": [{"role": "user", "content": "test"}],
        },
    )
    assert missing_provider_key_response.status_code == 400
    assert missing_provider_key_response.json()["detail"] == "Add an API key or save one for this provider"

    container.ask_dashboard_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(side_effect=LLMProxyError("Saved API key is unreadable, please save it again")),
    )

    unreadable_provider_key_response = await async_client.post(
        "/api/v1/ai/meta/ad-accounts/act_1/chat",
        json={
            "days": 30,
            "language": "kz",
            "use_client_credentials": True,
            "provider": "gemini",
            "messages": [{"role": "user", "content": "test"}],
        },
    )
    assert unreadable_provider_key_response.status_code == 400
    assert unreadable_provider_key_response.json()["detail"] == "Saved API key is unreadable, please save it again"


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


@pytest.mark.integration
@pytest.mark.api
async def test_auto_verdict_route_maps_internal_ai_configuration_error(async_client):
    container = FakeContainer()
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
    container.generate_auto_verdict_use_case.return_value = SimpleNamespace(
        execute=AsyncMock(side_effect=LLMProxyError("Internal AI summary is not configured")),
    )

    app.dependency_overrides[get_current_user] = _override_current_user
    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[get_di_container] = lambda: container

    response = await async_client.post(
        "/api/v1/ai/meta/ad-accounts/act_1/auto-verdict",
        json={"days": 30, "language": "ru"},
    )

    assert response.status_code == 200
    assert response.json()["text"] == "Короткий вывод появится после настройки серверного AI-ключа."
