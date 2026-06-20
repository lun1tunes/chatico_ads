from __future__ import annotations

import re

import httpx
import pytest
import respx

from core.infrastructure.meta_graph_api import MetaGraphAPIClient, MetaGraphAPIError


@pytest.mark.unit
@pytest.mark.service
def test_build_authorization_url_includes_config_id():
    client = MetaGraphAPIClient(
        graph_version="v24.0",
        client_id="app-id",
        client_secret="app-secret",
        redirect_uri="http://localhost/callback",
        oauth_scopes=["ads_read"],
        oauth_config_id="config-123",
    )

    url = client.build_authorization_url(state="signed-state")

    assert "client_id=app-id" in url
    assert "state=signed-state" in url
    assert "config_id=config-123" in url
    assert "scope=ads_read" in url


@pytest.mark.unit
@pytest.mark.service
@respx.mock
async def test_meta_graph_api_methods_share_common_get_transport():
    client = MetaGraphAPIClient(
        graph_version="v24.0",
        client_id="app-id",
        client_secret="app-secret",
        redirect_uri="http://localhost/callback",
        oauth_scopes=["ads_read"],
    )
    route = respx.route(method="GET", url__regex=re.compile(r"https://graph\.facebook\.com/v24\.0/.+")).mock(
        side_effect=[
            httpx.Response(200, json={"access_token": "token-1"}),
            httpx.Response(200, json={"access_token": "token-2"}),
            httpx.Response(200, json={"id": "me", "name": "Owner"}),
            httpx.Response(200, json={"data": [{"id": "act_1"}]}),
            httpx.Response(200, json={"id": "act_1", "name": "Main account"}),
            httpx.Response(200, json={"data": [{"id": "cmp_1"}]}),
            httpx.Response(200, json={"data": [{"spend": "10"}]}),
            httpx.Response(200, json={"data": [{"campaign_id": "cmp_1"}]}),
            httpx.Response(200, json={"data": [{"id": "ad_1"}]}),
            httpx.Response(200, json={"data": [{"ad_id": "ad_1"}]}),
        ]
    )

    assert await client.exchange_code_for_token(code="oauth-code") == {"access_token": "token-1"}
    assert await client.exchange_for_long_lived_token(access_token="token-1") == {"access_token": "token-2"}
    assert await client.get_me(access_token="token-2") == {"id": "me", "name": "Owner"}
    assert await client.list_ad_accounts(access_token="token-2") == [{"id": "act_1"}]
    assert await client.get_ad_account(account_id="act_1", access_token="token-2") == {
        "id": "act_1",
        "name": "Main account",
    }
    assert await client.list_campaigns(account_id="act_1", access_token="token-2") == [{"id": "cmp_1"}]
    assert await client.get_account_insights(
        account_id="act_1",
        access_token="token-2",
        since="2026-06-01",
        until="2026-06-15",
    ) == {"spend": "10"}
    assert await client.get_campaign_insights(
        account_id="act_1",
        access_token="token-2",
        since="2026-06-01",
        until="2026-06-15",
    ) == [{"campaign_id": "cmp_1"}]
    assert await client.list_ads(account_id="act_1", access_token="token-2") == [{"id": "ad_1"}]
    assert await client.get_ad_insights(
        account_id="act_1",
        access_token="token-2",
        since="2026-06-01",
        until="2026-06-15",
    ) == [{"ad_id": "ad_1"}]

    assert len(route.calls) == 10
    assert route.calls[0].request.url.params["code"] == "oauth-code"
    assert route.calls[6].request.url.params["level"] == "account"
    assert "object_story_spec" in route.calls[8].request.url.params["fields"]
    assert route.calls[9].request.url.params["level"] == "ad"
    await client.aclose()


@pytest.mark.unit
@pytest.mark.service
@respx.mock
async def test_meta_graph_api_raises_on_error():
    client = MetaGraphAPIClient(graph_version="v24.0")
    respx.get("https://graph.facebook.com/v24.0/me").mock(
        return_value=httpx.Response(400, json={"error": {"message": "Meta failure"}})
    )

    with pytest.raises(MetaGraphAPIError, match="Meta failure"):
        await client.get_me(access_token="bad-token")
    await client.aclose()


@pytest.mark.unit
@pytest.mark.service
@respx.mock
async def test_meta_graph_api_follows_pagination_links():
    client = MetaGraphAPIClient(graph_version="v24.0")
    route = respx.route(
        method="GET",
        url__regex=re.compile(r"https://graph\.facebook\.com/v24\.0/act_1/campaigns(?:\?.*)?$"),
    ).mock(
        side_effect=[
            httpx.Response(
                200,
                json={
                    "data": [{"id": "cmp_1"}],
                    "paging": {"next": "https://graph.facebook.com/v24.0/act_1/campaigns?after=cursor-1"},
                },
            ),
            httpx.Response(200, json={"data": [{"id": "cmp_2"}]}),
        ]
    )

    campaigns = await client.list_campaigns(account_id="act_1", access_token="token-1")

    assert campaigns == [{"id": "cmp_1"}, {"id": "cmp_2"}]
    assert len(route.calls) == 2
    await client.aclose()


@pytest.mark.unit
@pytest.mark.service
@respx.mock
async def test_meta_graph_api_raises_on_transport_error():
    client = MetaGraphAPIClient(graph_version="v24.0")
    respx.get("https://graph.facebook.com/v24.0/me").mock(side_effect=httpx.ConnectTimeout("timed out"))

    with pytest.raises(MetaGraphAPIError, match="Meta API request failed"):
        await client.get_me(access_token="bad-token")
    await client.aclose()
