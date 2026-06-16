from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.meta_ad_account import MetaAdAccountRepository
from ..services.meta_report_service import MetaReportService


class GenerateMetaReportUseCase:
    def __init__(self, *, session: AsyncSession, date_range_service, report_service: MetaReportService) -> None:
        self.date_range_service = date_range_service
        self.report_service = report_service
        self.account_repo = MetaAdAccountRepository(session)

    async def execute(self, *, user_id: str, ad_account_id: str, days: int) -> dict[str, object]:
        periods = self.date_range_service.build_periods(days=days)
        return await self.report_service.build_report(
            account_repo=self.account_repo,
            user_id=user_id,
            external_account_id=ad_account_id,
            periods=periods,
        )


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


class AskDashboardUseCase:
    def __init__(self, *, llm_proxy_service) -> None:
        self.llm_proxy_service = llm_proxy_service

    async def execute(
        self,
        *,
        provider: str,
        api_key: str,
        model: str | None,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> str:
        return await self.llm_proxy_service.chat(
            provider=provider,
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            messages=messages,
        )
