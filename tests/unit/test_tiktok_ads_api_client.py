from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from core.infrastructure.tiktok_ads_api import TikTokAdsAPIClient


@pytest.mark.unit
def test_tiktok_ads_client_builds_oauth_url():
    client = TikTokAdsAPIClient(
        app_id="test-tiktok-app-id",
        app_secret="test-tiktok-app-secret",
        redirect_uri="http://localhost:8000/api/v1/tiktok-ads/oauth/callback",
        oauth_scopes=["ads.read", "reporting"],
    )

    authorization_url = client.build_authorization_url(state="tiktok-signed-state-token")
    params = parse_qs(urlparse(authorization_url).query)

    assert authorization_url.startswith("https://ads.tiktok.com/marketing_api/auth?")
    assert params["app_id"][0] == "test-tiktok-app-id"
    assert params["redirect_uri"][0] == "http://localhost:8000/api/v1/tiktok-ads/oauth/callback"
    assert params["state"][0] == "tiktok-signed-state-token"
    assert params["scope"][0] == "ads.read,reporting"
