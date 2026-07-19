from __future__ import annotations

import pytest
from cryptography.fernet import Fernet

from core.infrastructure.llm_clients import LLMProxyError
from core.models.db_helper import db_helper
from core.models.user import User
from core.repositories.user_ai_provider_key import UserAIProviderKeyRepository
from core.security.encryption_service import EncryptionService
from core.use_cases.dashboard import (
    AskDashboardUseCase,
    DeleteAIProviderKeyUseCase,
    GenerateAutoVerdictUseCase,
    ListSavedAIProviderKeysUseCase,
    SaveAIProviderKeyUseCase,
)


class FakeLLMProxyService:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.internal_calls: list[dict[str, object]] = []
        self.auto_verdict_calls: list[dict[str, object]] = []

    def normalize_provider(self, provider: str) -> str:
        normalized = provider.strip().lower()
        if normalized not in {"anthropic", "openai", "gemini"}:
            raise LLMProxyError("Unsupported AI provider")
        return normalized

    async def chat(self, **kwargs):
        self.calls.append(kwargs)
        return "chat-ok"

    async def chat_with_internal_credentials(self, **kwargs):
        self.internal_calls.append(kwargs)
        return "internal-chat-ok"

    async def generate_auto_verdict(self, **kwargs):
        self.auto_verdict_calls.append(kwargs)
        return "verdict-ok"


@pytest.mark.unit
@pytest.mark.use_case
async def test_save_list_and_delete_ai_provider_key_use_cases(db_session):
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="ru"))
    await db_session.commit()

    llm_proxy_service = FakeLLMProxyService()
    encryption_service = EncryptionService()

    saved = await SaveAIProviderKeyUseCase(
        session=db_session,
        encryption_service=encryption_service,
        llm_proxy_service=llm_proxy_service,
    ).execute(user_id="user-1", provider="Gemini", api_key="gemini-client-key-123")

    assert saved["provider"] == "gemini"
    assert saved["has_saved_key"] is True

    repository = UserAIProviderKeyRepository(db_session)
    credential = await repository.get_by_user_and_provider(user_id="user-1", provider="gemini")
    assert credential is not None
    assert encryption_service.decrypt(credential.api_key_encrypted) == "gemini-client-key-123"

    listed = await ListSavedAIProviderKeysUseCase(session=db_session).execute(user_id="user-1")
    assert listed == [
        {
            "provider": "gemini",
            "has_saved_key": True,
            "updated_at": credential.updated_at,
        }
    ]

    await DeleteAIProviderKeyUseCase(
        session=db_session,
        llm_proxy_service=llm_proxy_service,
    ).execute(user_id="user-1", provider="gemini")

    async with db_helper.session_factory() as verification_session:
        fresh_repository = UserAIProviderKeyRepository(verification_session)
        assert await fresh_repository.get_by_user_and_provider(user_id="user-1", provider="gemini") is None


@pytest.mark.unit
@pytest.mark.use_case
async def test_ask_dashboard_use_case_uses_internal_chat_when_client_credentials_disabled(db_session):
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="ru"))
    await db_session.commit()

    llm_proxy_service = FakeLLMProxyService()

    text = await AskDashboardUseCase(
        session=db_session,
        llm_proxy_service=llm_proxy_service,
        encryption_service=EncryptionService(),
    ).execute(
        user_id="user-1",
        use_client_credentials=False,
        provider=None,
        api_key=None,
        model=None,
        system_prompt="system prompt",
        messages=[{"role": "user", "content": "What changed?"}],
    )

    assert text == "internal-chat-ok"
    assert llm_proxy_service.calls == []
    assert llm_proxy_service.internal_calls[0]["system_prompt"] == "system prompt"


@pytest.mark.unit
@pytest.mark.use_case
async def test_generate_auto_verdict_use_case_uses_internal_credentials_when_client_credentials_disabled(db_session):
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="ru"))
    await db_session.commit()

    llm_proxy_service = FakeLLMProxyService()

    text = await GenerateAutoVerdictUseCase(
        session=db_session,
        llm_proxy_service=llm_proxy_service,
        encryption_service=EncryptionService(),
    ).execute(
        user_id="user-1",
        use_client_credentials=False,
        provider=None,
        api_key=None,
        model=None,
        report_context="dashboard context",
        language="ru",
    )

    assert text == "verdict-ok"
    assert llm_proxy_service.auto_verdict_calls == [
        {
            "report_context": "dashboard context",
            "language": "ru",
        }
    ]


@pytest.mark.unit
@pytest.mark.use_case
async def test_ask_dashboard_use_case_uses_saved_provider_key_when_request_key_missing(db_session):
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="ru"))
    await db_session.commit()

    llm_proxy_service = FakeLLMProxyService()
    encryption_service = EncryptionService()
    await SaveAIProviderKeyUseCase(
        session=db_session,
        encryption_service=encryption_service,
        llm_proxy_service=llm_proxy_service,
    ).execute(user_id="user-1", provider="gemini", api_key="saved-gemini-key-123")

    text = await AskDashboardUseCase(
        session=db_session,
        llm_proxy_service=llm_proxy_service,
        encryption_service=encryption_service,
    ).execute(
        user_id="user-1",
        use_client_credentials=True,
        provider="gemini",
        api_key=None,
        model=None,
        system_prompt="system prompt",
        messages=[{"role": "user", "content": "What changed?"}],
    )

    credential = await UserAIProviderKeyRepository(db_session).get_by_user_and_provider(
        user_id="user-1", provider="gemini"
    )

    assert text == "chat-ok"
    assert llm_proxy_service.calls[0]["api_key"] == "saved-gemini-key-123"
    assert credential is not None
    assert credential.last_used_at is not None


@pytest.mark.unit
@pytest.mark.use_case
async def test_generate_auto_verdict_use_case_uses_saved_provider_key_when_request_key_missing(db_session):
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="ru"))
    await db_session.commit()

    llm_proxy_service = FakeLLMProxyService()
    encryption_service = EncryptionService()
    await SaveAIProviderKeyUseCase(
        session=db_session,
        encryption_service=encryption_service,
        llm_proxy_service=llm_proxy_service,
    ).execute(user_id="user-1", provider="gemini", api_key="saved-gemini-key-123")

    text = await GenerateAutoVerdictUseCase(
        session=db_session,
        llm_proxy_service=llm_proxy_service,
        encryption_service=encryption_service,
    ).execute(
        user_id="user-1",
        use_client_credentials=True,
        provider="gemini",
        api_key=None,
        model=None,
        report_context="dashboard context",
        language="ru",
    )

    credential = await UserAIProviderKeyRepository(db_session).get_by_user_and_provider(
        user_id="user-1", provider="gemini"
    )

    assert text == "verdict-ok"
    assert llm_proxy_service.auto_verdict_calls[0]["api_key"] == "saved-gemini-key-123"
    assert llm_proxy_service.auto_verdict_calls[0]["provider"] == "gemini"
    assert credential is not None
    assert credential.last_used_at is not None


@pytest.mark.unit
@pytest.mark.use_case
async def test_ask_dashboard_use_case_rejects_missing_request_and_saved_provider_key(db_session):
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="ru"))
    await db_session.commit()

    with pytest.raises(LLMProxyError, match="Add an API key or save one for this provider"):
        await AskDashboardUseCase(
            session=db_session,
            llm_proxy_service=FakeLLMProxyService(),
            encryption_service=EncryptionService(),
        ).execute(
            user_id="user-1",
            use_client_credentials=True,
            provider="openai",
            api_key=None,
            model=None,
            system_prompt="system prompt",
            messages=[{"role": "user", "content": "What changed?"}],
        )


@pytest.mark.unit
@pytest.mark.use_case
async def test_ask_dashboard_use_case_rejects_unreadable_saved_provider_key(db_session):
    db_session.add(User(id="user-1", email="owner@example.com", password_hash="hash", locale="ru"))
    await db_session.commit()

    llm_proxy_service = FakeLLMProxyService()
    encryption_service = EncryptionService()
    await SaveAIProviderKeyUseCase(
        session=db_session,
        encryption_service=encryption_service,
        llm_proxy_service=llm_proxy_service,
    ).execute(user_id="user-1", provider="gemini", api_key="saved-gemini-key-123")

    broken_encryption_service = EncryptionService(key=Fernet.generate_key().decode())

    with pytest.raises(LLMProxyError, match="Saved API key is unreadable, please save it again"):
        await AskDashboardUseCase(
            session=db_session,
            llm_proxy_service=llm_proxy_service,
            encryption_service=broken_encryption_service,
        ).execute(
            user_id="user-1",
            use_client_credentials=True,
            provider="gemini",
            api_key=None,
            model=None,
            system_prompt="system prompt",
            messages=[{"role": "user", "content": "What changed?"}],
        )
