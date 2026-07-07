from __future__ import annotations

import jwt
import pytest

from core.services.tiktok_ads_state_service import TikTokAdsOAuthStateService


@pytest.mark.unit
def test_tiktok_ads_state_service_round_trip():
    service = TikTokAdsOAuthStateService()

    token = service.create_state_token(user_id="user-1")
    payload = service.decode_state_token(token)

    assert payload["sub"] == "user-1"
    assert payload["type"] == "tiktok_ads_oauth_state"


@pytest.mark.unit
def test_tiktok_ads_state_service_rejects_wrong_token_type():
    service = TikTokAdsOAuthStateService()
    valid_token = service.create_state_token(user_id="user-1")
    payload = jwt.decode(valid_token, options={"verify_signature": False})
    payload["type"] = "meta_oauth_state"
    forged_token = jwt.encode(payload, "test-secret-key-with-at-least-thirty-two-bytes", algorithm="HS256")

    with pytest.raises(jwt.InvalidTokenError):
        service.decode_state_token(forged_token)
