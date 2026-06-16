from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.repositories.meta_connection import MetaConnectionRepository
from core.security.encryption_service import EncryptionService
from core.use_cases.meta import BuildMetaOAuthUrlUseCase, HandleMetaOAuthCallbackUseCase, ListMetaAdAccountsUseCase
from core.models.user import User


class FakeStateService:
    def __init__(self) -> None:
        self.created_for: str | None = None

    def create_state_token(self, *, user_id: str) -> str:
        self.created_for = user_id
        return "signed-state-token"

    def decode_state_token(self, state: str) -> dict[str, str]:
        assert state == "signed-state-token"
        return {"sub": "user-1"}


class FakeMetaClient:
    def build_authorization_url(self, *, state: str) -> str:
        return f"https://facebook.test/oauth?state={state}"

    async def exchange_code_for_token(self, *, code: str) -> dict[str, object]:
        assert code == "code-1"
        return {"access_token": "short-lived-token", "expires_in": 3600, "scope": ["ads_read"]}

    async def exchange_for_long_lived_token(self, *, access_token: str) -> dict[str, object]:
        assert access_token == "short-lived-token"
        return {"access_token": "long-lived-token", "expires_in": 7200, "scope": ["ads_read"]}

    async def get_me(self, *, access_token: str) -> dict[str, object]:
        assert access_token == "long-lived-token"
        return {"id": "meta-user-1", "name": "Meta Owner"}

    async def list_ad_accounts(self, *, access_token: str) -> list[dict[str, object]]:
        assert access_token == "long-lived-token"
        return [
            {
                "id": "act_1",
                "account_id": "111",
                "name": "Main account",
                "currency": "USD",
                "timezone_name": "Asia/Almaty",
                "account_status": 1,
            },
            {
                "id": "act_2",
                "account_id": "222",
                "name": "Backup account",
                "currency": "KZT",
                "timezone_name": "Asia/Almaty",
                "account_status": 2,
            },
        ]


@pytest.mark.unit
@pytest.mark.use_case
async def test_build_meta_oauth_url_use_case():
    state_service = FakeStateService()
    use_case = BuildMetaOAuthUrlUseCase(state_service=state_service, meta_client=FakeMetaClient())

    result = await use_case.execute(user_id="user-1")

    assert result["authorization_url"] == "https://facebook.test/oauth?state=signed-state-token"
    assert state_service.created_for == "user-1"


@pytest.mark.unit
@pytest.mark.use_case
async def test_handle_meta_oauth_callback_persists_connection_and_accounts(db_session):
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="kz"))
    await db_session.commit()

    state_service = FakeStateService()
    encryption_service = EncryptionService()
    use_case = HandleMetaOAuthCallbackUseCase(
        session=db_session,
        state_service=state_service,
        meta_client=FakeMetaClient(),
        encryption_service=encryption_service,
    )

    result = await use_case.execute(code="code-1", state="signed-state-token")

    assert result["user_id"] == "user-1"

    connection = await MetaConnectionRepository(db_session).get_by_user_and_meta_user(
        user_id="user-1",
        meta_user_id="meta-user-1",
    )
    assert connection is not None
    assert connection.meta_user_name == "Meta Owner"
    assert encryption_service.decrypt(connection.access_token_encrypted) == "long-lived-token"
    assert connection.scopes == "ads_read"
    assert len(connection.ad_accounts) == 2

    ad_accounts = await ListMetaAdAccountsUseCase(session=db_session).execute(user_id="user-1")
    assert [account.external_id for account in ad_accounts] == ["act_2", "act_1"]
    assert ad_accounts[0].currency == "KZT"
