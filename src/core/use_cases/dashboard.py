from __future__ import annotations

from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ..infrastructure.llm_clients import LLMProxyError
from ..repositories.meta_ad_account import MetaAdAccountRepository
from ..repositories.meta_report_snapshot import MetaReportSnapshotRepository
from ..repositories.user_ai_provider_key import UserAIProviderKeyRepository
from ..models.user_ai_provider_key import UserAIProviderKey
from ..services.meta_report_service import MetaReportService
from ..utils.time import utcnow


class GenerateMetaReportUseCase:
    def __init__(self, *, session: AsyncSession, date_range_service, report_service: MetaReportService) -> None:
        self.session = session
        self.date_range_service = date_range_service
        self.report_service = report_service
        self.account_repo = MetaAdAccountRepository(session)
        self.snapshot_repo = MetaReportSnapshotRepository(session)

    async def execute(
        self,
        *,
        user_id: str,
        ad_account_id: str,
        days: int,
        force_refresh: bool = False,
    ) -> dict[str, object]:
        periods = self.date_range_service.build_periods(days=days)
        report = await self.report_service.build_report(
            account_repo=self.account_repo,
            snapshot_repo=self.snapshot_repo,
            user_id=user_id,
            external_account_id=ad_account_id,
            requested_days=days,
            periods=periods,
            force_refresh=force_refresh,
        )
        await self.session.commit()
        return report


class GenerateAutoVerdictUseCase:
    def __init__(self, *, llm_proxy_service) -> None:
        self.llm_proxy_service = llm_proxy_service

    async def execute(self, *, report_context: str, language: str) -> str:
        return await self.llm_proxy_service.generate_auto_verdict(report_context=report_context, language=language)


class ListSupportedAIProvidersUseCase:
    def __init__(self, *, llm_proxy_service) -> None:
        self.llm_proxy_service = llm_proxy_service

    def execute(self) -> list[dict[str, object]]:
        return self.llm_proxy_service.list_supported_providers()


class ListSavedAIProviderKeysUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self.key_repo = UserAIProviderKeyRepository(session)

    async def execute(self, *, user_id: str) -> list[dict[str, object]]:
        credentials = await self.key_repo.list_by_user(user_id=user_id)
        return [
            {
                "provider": credential.provider,
                "has_saved_key": True,
                "updated_at": credential.updated_at,
            }
            for credential in credentials
        ]


class SaveAIProviderKeyUseCase:
    def __init__(self, *, session: AsyncSession, encryption_service, llm_proxy_service) -> None:
        self.session = session
        self.encryption_service = encryption_service
        self.llm_proxy_service = llm_proxy_service
        self.key_repo = UserAIProviderKeyRepository(session)

    async def execute(self, *, user_id: str, provider: str, api_key: str) -> dict[str, object]:
        normalized_provider = self.llm_proxy_service.normalize_provider(provider)
        normalized_key = api_key.strip()

        credential = await self.key_repo.get_by_user_and_provider(user_id=user_id, provider=normalized_provider)
        encrypted_key = self.encryption_service.encrypt(normalized_key)
        if credential is None:
            credential = UserAIProviderKey(
                id=str(uuid4()),
                user_id=user_id,
                provider=normalized_provider,
                api_key_encrypted=encrypted_key,
            )
            await self.key_repo.create(credential)
        else:
            credential.api_key_encrypted = encrypted_key

        await self.session.commit()
        return {
            "provider": credential.provider,
            "has_saved_key": True,
            "updated_at": credential.updated_at,
        }


class DeleteAIProviderKeyUseCase:
    def __init__(self, *, session: AsyncSession, llm_proxy_service) -> None:
        self.session = session
        self.llm_proxy_service = llm_proxy_service
        self.key_repo = UserAIProviderKeyRepository(session)

    async def execute(self, *, user_id: str, provider: str) -> None:
        normalized_provider = self.llm_proxy_service.normalize_provider(provider)
        credential = await self.key_repo.get_by_user_and_provider(user_id=user_id, provider=normalized_provider)
        if credential is None:
            return

        await self.key_repo.delete(credential)
        await self.session.commit()


class AskDashboardUseCase:
    def __init__(self, *, session: AsyncSession, llm_proxy_service, encryption_service) -> None:
        self.session = session
        self.llm_proxy_service = llm_proxy_service
        self.encryption_service = encryption_service
        self.key_repo = UserAIProviderKeyRepository(session)

    async def execute(
        self,
        *,
        user_id: str,
        use_client_credentials: bool,
        provider: str | None,
        api_key: str | None,
        model: str | None,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> str:
        if not use_client_credentials:
            return await self.llm_proxy_service.chat_with_internal_credentials(
                system_prompt=system_prompt,
                messages=messages,
            )

        normalized_provider = self.llm_proxy_service.normalize_provider(provider or "gemini")
        resolved_api_key = api_key.strip() if api_key else ""
        credential = None

        if not resolved_api_key:
            credential = await self.key_repo.get_by_user_and_provider(user_id=user_id, provider=normalized_provider)
            if credential is None:
                raise LLMProxyError("Add an API key or save one for this provider")
            try:
                resolved_api_key = self.encryption_service.decrypt(credential.api_key_encrypted)
            except Exception as exc:  # noqa: BLE001
                raise LLMProxyError("Saved API key is unreadable, please save it again") from exc

        response_text = await self.llm_proxy_service.chat(
            provider=normalized_provider,
            api_key=resolved_api_key,
            model=model,
            system_prompt=system_prompt,
            messages=messages,
        )

        if credential is not None:
            credential.last_used_at = utcnow()
            await self.session.commit()

        return response_text
