from __future__ import annotations

import asyncio
from urllib.parse import parse_qs, urlparse

import pytest

from core.models.db_helper import db_helper
from core.models.user import User
from core.repositories.google_ads_connection import GoogleAdsConnectionRepository
from core.security.encryption_service import EncryptionService
from core.infrastructure.google_ads_api import GoogleAdsAPIClient
from core.use_cases.google_ads import (
    BuildGoogleAdsOAuthUrlUseCase,
    HandleGoogleAdsOAuthCallbackUseCase,
    ListGoogleAdsCustomersUseCase,
)


class FakeGoogleStateService:
    def __init__(self) -> None:
        self.created_for: str | None = None

    def create_state_token(self, *, user_id: str) -> str:
        self.created_for = user_id
        return "google-signed-state-token"

    def decode_state_token(self, state: str) -> dict[str, str]:
        assert state == "google-signed-state-token"
        return {"sub": "user-1"}


class FakeGoogleAdsClient:
    def __init__(self, *, customers: list[dict[str, object]] | None = None) -> None:
        self.customers = customers or self.default_customers()

    @staticmethod
    def default_customers() -> list[dict[str, object]]:
        return [
            {
                "external_customer_id": "1234567890",
                "resource_name": "customers/1234567890",
                "descriptive_name": "Direct account",
                "currency_code": "USD",
                "time_zone": "Europe/Paris",
                "is_manager": False,
                "is_directly_accessible": True,
                "hierarchy_level": 0,
                "root_customer_id": "1234567890",
                "manager_customer_id": None,
                "login_customer_id": None,
            },
            {
                "external_customer_id": "9988776655",
                "resource_name": "customers/9988776655",
                "descriptive_name": "Main MCC",
                "currency_code": "USD",
                "time_zone": "Europe/Paris",
                "is_manager": True,
                "is_directly_accessible": True,
                "hierarchy_level": 0,
                "root_customer_id": "9988776655",
                "manager_customer_id": None,
                "login_customer_id": None,
            },
            {
                "external_customer_id": "5566778899",
                "resource_name": "customers/5566778899",
                "descriptive_name": "Managed client",
                "currency_code": "KZT",
                "time_zone": "Asia/Almaty",
                "is_manager": False,
                "is_directly_accessible": False,
                "hierarchy_level": 1,
                "root_customer_id": "9988776655",
                "manager_customer_id": "9988776655",
                "login_customer_id": "9988776655",
            },
        ]

    def build_authorization_url(self, *, state: str) -> str:
        return f"https://accounts.google.test/o/oauth2/v2/auth?state={state}"

    async def exchange_code_for_tokens(self, *, code: str) -> dict[str, object]:
        assert code == "google-code-1"
        return {
            "access_token": "google-access-token",
            "refresh_token": "google-refresh-token",
            "expires_in": 3600,
            "scope": "https://www.googleapis.com/auth/adwords",
        }

    async def list_customer_accounts(self, *, access_token: str) -> list[dict[str, object]]:
        assert access_token == "google-access-token"
        return self.customers


@pytest.mark.unit
@pytest.mark.use_case
async def test_build_google_ads_oauth_url_use_case():
    state_service = FakeGoogleStateService()
    use_case = BuildGoogleAdsOAuthUrlUseCase(state_service=state_service, google_ads_client=FakeGoogleAdsClient())

    result = await use_case.execute(user_id="user-1")

    assert result["authorization_url"] == (
        "https://accounts.google.test/o/oauth2/v2/auth?state=google-signed-state-token"
    )
    assert state_service.created_for == "user-1"


@pytest.mark.unit
@pytest.mark.use_case
async def test_handle_google_ads_oauth_callback_persists_connection_and_customers(db_session):
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="ru"))
    await db_session.commit()

    use_case = HandleGoogleAdsOAuthCallbackUseCase(
        session=db_session,
        state_service=FakeGoogleStateService(),
        google_ads_client=FakeGoogleAdsClient(),
        encryption_service=EncryptionService(),
    )

    result = await use_case.execute(code="google-code-1", state="google-signed-state-token")

    assert result["user_id"] == "user-1"
    assert result["customer_count"] == 3

    async with db_helper.session_factory() as verification_session:
        connection = await GoogleAdsConnectionRepository(verification_session).get_by_user(user_id="user-1")
        assert connection is not None
        assert len(connection.customers) == 3

        customers = await ListGoogleAdsCustomersUseCase(session=verification_session).execute(user_id="user-1")
        assert [customer.external_customer_id for customer in customers] == ["9988776655", "1234567890", "5566778899"]

        managed_customer = next(customer for customer in customers if customer.external_customer_id == "5566778899")
        assert managed_customer.login_customer_id == "9988776655"
        assert managed_customer.is_directly_accessible is False


@pytest.mark.unit
@pytest.mark.use_case
async def test_handle_google_ads_oauth_callback_removes_stale_customers_on_resync(db_session):
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="ru"))
    await db_session.commit()

    encryption_service = EncryptionService()
    initial_client = FakeGoogleAdsClient()
    use_case = HandleGoogleAdsOAuthCallbackUseCase(
        session=db_session,
        state_service=FakeGoogleStateService(),
        google_ads_client=initial_client,
        encryption_service=encryption_service,
    )
    await use_case.execute(code="google-code-1", state="google-signed-state-token")

    reduced_customer_set = FakeGoogleAdsClient.default_customers()[:2]
    resync_use_case = HandleGoogleAdsOAuthCallbackUseCase(
        session=db_session,
        state_service=FakeGoogleStateService(),
        google_ads_client=FakeGoogleAdsClient(customers=reduced_customer_set),
        encryption_service=encryption_service,
    )
    await resync_use_case.execute(code="google-code-1", state="google-signed-state-token")

    async with db_helper.session_factory() as verification_session:
        connection = await GoogleAdsConnectionRepository(verification_session).get_by_user(user_id="user-1")
        assert connection is not None
        assert [customer.external_customer_id for customer in connection.customers] == ["1234567890", "9988776655"]


@pytest.mark.unit
@pytest.mark.use_case
def test_google_ads_client_builds_oauth_url_with_offline_consent_parameters():
    client = GoogleAdsAPIClient(
        developer_token="test-google-developer-token",
        client_id="test-google-client-id",
        client_secret="test-google-client-secret",
        redirect_uri="http://localhost:8000/api/v1/google-ads/oauth/callback",
    )

    authorization_url = client.build_authorization_url(state="google-signed-state-token")
    params = parse_qs(urlparse(authorization_url).query)

    assert authorization_url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert params["client_id"][0] == "test-google-client-id"
    assert params["redirect_uri"][0] == "http://localhost:8000/api/v1/google-ads/oauth/callback"
    assert params["response_type"][0] == "code"
    assert params["access_type"][0] == "offline"
    assert params["include_granted_scopes"][0] == "true"
    assert params["prompt"][0] == "consent"
    assert params["scope"][0] == "https://www.googleapis.com/auth/adwords"
    assert params["state"][0] == "google-signed-state-token"
    asyncio.run(client.aclose())
