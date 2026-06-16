from __future__ import annotations

import pytest

from core.security.jwt_service import JWTService
from core.services.meta_state_service import MetaOAuthStateService


@pytest.mark.unit
@pytest.mark.service
def test_meta_state_service_roundtrip():
    service = MetaOAuthStateService()

    token = service.create_state_token(user_id="user-123")
    payload = service.decode_state_token(token)

    assert payload["sub"] == "user-123"
    assert payload["type"] == "meta_oauth_state"


@pytest.mark.unit
@pytest.mark.service
def test_jwt_service_roundtrip():
    service = JWTService(secret_key="secret-key-with-at-least-thirty-two-bytes", access_minutes=15, refresh_days=7)

    access_token = service.create_access_token(subject="user-1")
    refresh_token = service.create_refresh_token(subject="user-1", session_id="session-1")

    assert service.decode_access_token(access_token)["sub"] == "user-1"
    assert service.decode_refresh_token(refresh_token)["sid"] == "session-1"
    assert service.hash_refresh_token(refresh_token)
