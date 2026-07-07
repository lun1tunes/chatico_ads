from __future__ import annotations

from urllib.parse import parse_qs, urlparse

import pytest

from core.models.db_helper import db_helper
from core.models.user import User
from core.repositories.tiktok_ads_connection import TikTokAdsConnectionRepository
from core.security.encryption_service import EncryptionService
from core.use_cases.tiktok_ads import (
    BuildTikTokAdsOAuthUrlUseCase,
    HandleTikTokAdsOAuthCallbackUseCase,
    ListTikTokAdsAdvertisersUseCase,
)


class FakeTikTokStateService:
    def __init__(self) -> None:
        self.created_for: str | None = None

    def create_state_token(self, *, user_id: str) -> str:
        self.created_for = user_id
        return "tiktok-signed-state-token"

    def decode_state_token(self, state: str) -> dict[str, str]:
        assert state == "tiktok-signed-state-token"
        return {"sub": "user-1"}


class FakeTikTokAdsClient:
    def __init__(self, *, advertiser_ids: list[str] | None = None) -> None:
        self.advertiser_ids = advertiser_ids or ["1234567890123456789", "998877665544332211"]

    def build_authorization_url(self, *, state: str) -> str:
        return f"https://ads.tiktok.test/marketing_api/auth?state={state}"

    async def exchange_code_for_tokens(self, *, code: str) -> dict[str, object]:
        assert code == "tiktok-code-1"
        return {
            "access_token": "tiktok-access-token",
            "refresh_token": "tiktok-refresh-token",
            "expires_in": 3600,
            "scope": "ads.read reporting",
        }

    async def list_authorized_advertiser_ids(self, *, access_token: str) -> list[str]:
        assert access_token == "tiktok-access-token"
        return self.advertiser_ids

    async def get_advertiser_info(
        self,
        *,
        advertiser_ids: list[str],
        access_token: str,
    ) -> list[dict[str, object]]:
        assert advertiser_ids == self.advertiser_ids
        assert access_token == "tiktok-access-token"
        catalog = {
            "1234567890123456789": {
                "advertiser_id": "1234567890123456789",
                "name": "TikTok Main Advertiser",
                "currency": "USD",
                "timezone": "Asia/Almaty",
                "status": "ACTIVE",
            },
            "998877665544332211": {
                "advertiser_id": "998877665544332211",
                "name": "TikTok Backup Advertiser",
                "currency": "KZT",
                "timezone_name": "Europe/Paris",
                "advertiser_status": "DISABLED",
            },
        }
        return [catalog[advertiser_id] for advertiser_id in advertiser_ids]


@pytest.mark.unit
@pytest.mark.use_case
async def test_build_tiktok_ads_oauth_url_use_case():
    state_service = FakeTikTokStateService()
    use_case = BuildTikTokAdsOAuthUrlUseCase(state_service=state_service, tiktok_ads_client=FakeTikTokAdsClient())

    result = await use_case.execute(user_id="user-1")
    params = parse_qs(urlparse(result["authorization_url"]).query)

    assert params["state"][0] == "tiktok-signed-state-token"
    assert state_service.created_for == "user-1"


@pytest.mark.unit
@pytest.mark.use_case
async def test_handle_tiktok_ads_oauth_callback_persists_connection_and_advertisers(db_session):
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="ru"))
    await db_session.commit()

    use_case = HandleTikTokAdsOAuthCallbackUseCase(
        session=db_session,
        state_service=FakeTikTokStateService(),
        tiktok_ads_client=FakeTikTokAdsClient(),
        encryption_service=EncryptionService(),
    )

    result = await use_case.execute(code="tiktok-code-1", state="tiktok-signed-state-token")

    assert result["user_id"] == "user-1"
    assert result["advertiser_count"] == 2

    async with db_helper.session_factory() as verification_session:
        connection = await TikTokAdsConnectionRepository(verification_session).get_by_user(user_id="user-1")
        assert connection is not None
        assert len(connection.advertisers) == 2

        advertisers = await ListTikTokAdsAdvertisersUseCase(session=verification_session).execute(user_id="user-1")
        assert [advertiser.advertiser_id for advertiser in advertisers] == [
            "998877665544332211",
            "1234567890123456789",
        ]
        assert advertisers[0].currency == "KZT"
        assert advertisers[1].name == "TikTok Main Advertiser"


@pytest.mark.unit
@pytest.mark.use_case
async def test_handle_tiktok_ads_oauth_callback_removes_stale_advertisers_on_resync(db_session):
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="ru"))
    await db_session.commit()

    encryption_service = EncryptionService()
    initial_use_case = HandleTikTokAdsOAuthCallbackUseCase(
        session=db_session,
        state_service=FakeTikTokStateService(),
        tiktok_ads_client=FakeTikTokAdsClient(),
        encryption_service=encryption_service,
    )
    await initial_use_case.execute(code="tiktok-code-1", state="tiktok-signed-state-token")

    reduced_use_case = HandleTikTokAdsOAuthCallbackUseCase(
        session=db_session,
        state_service=FakeTikTokStateService(),
        tiktok_ads_client=FakeTikTokAdsClient(advertiser_ids=["1234567890123456789"]),
        encryption_service=encryption_service,
    )
    await reduced_use_case.execute(code="tiktok-code-1", state="tiktok-signed-state-token")

    async with db_helper.session_factory() as verification_session:
        connection = await TikTokAdsConnectionRepository(verification_session).get_by_user(user_id="user-1")
        assert connection is not None
        assert [advertiser.advertiser_id for advertiser in connection.advertisers] == ["1234567890123456789"]
