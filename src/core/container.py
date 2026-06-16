from __future__ import annotations

from dependency_injector import containers, providers

from .infrastructure.llm_clients import AnthropicClient, GeminiClient, OpenAIClient
from .infrastructure.meta_graph_api import MetaGraphAPIClient
from .security.encryption_service import EncryptionService
from .security.jwt_service import JWTService
from .security.password_service import PasswordService
from .services.date_range_service import DateRangeService
from .services.llm_proxy_service import LLMProxyService
from .services.meta_report_service import MetaReportService
from .services.meta_state_service import MetaOAuthStateService
from .use_cases.auth import LoginUserUseCase, LogoutUserUseCase, RefreshSessionUseCase, RegisterUserUseCase
from .use_cases.dashboard import AskDashboardUseCase, GenerateAutoVerdictUseCase, GenerateMetaReportUseCase
from .use_cases.meta import BuildMetaOAuthUrlUseCase, HandleMetaOAuthCallbackUseCase, ListMetaAdAccountsUseCase


class Container(containers.DeclarativeContainer):
    password_service = providers.Singleton(PasswordService)
    encryption_service = providers.Singleton(EncryptionService)
    jwt_service = providers.Singleton(JWTService)
    meta_state_service = providers.Singleton(MetaOAuthStateService)
    date_range_service = providers.Singleton(DateRangeService)

    meta_client = providers.Singleton(MetaGraphAPIClient)
    anthropic_client = providers.Singleton(AnthropicClient)
    openai_client = providers.Singleton(OpenAIClient)
    gemini_client = providers.Singleton(GeminiClient)

    llm_proxy_service = providers.Singleton(
        LLMProxyService,
        anthropic_client=anthropic_client,
        openai_client=openai_client,
        gemini_client=gemini_client,
    )
    meta_report_service = providers.Singleton(
        MetaReportService,
        meta_client=meta_client,
        encryption_service=encryption_service,
    )

    register_user_use_case = providers.Factory(
        RegisterUserUseCase,
        password_service=password_service,
        jwt_service=jwt_service,
    )
    login_user_use_case = providers.Factory(
        LoginUserUseCase,
        password_service=password_service,
        jwt_service=jwt_service,
    )
    refresh_session_use_case = providers.Factory(RefreshSessionUseCase, jwt_service=jwt_service)
    logout_user_use_case = providers.Factory(LogoutUserUseCase, jwt_service=jwt_service)

    build_meta_oauth_url_use_case = providers.Factory(
        BuildMetaOAuthUrlUseCase,
        state_service=meta_state_service,
        meta_client=meta_client,
    )
    handle_meta_oauth_callback_use_case = providers.Factory(
        HandleMetaOAuthCallbackUseCase,
        state_service=meta_state_service,
        meta_client=meta_client,
        encryption_service=encryption_service,
    )
    list_meta_ad_accounts_use_case = providers.Factory(ListMetaAdAccountsUseCase)

    generate_meta_report_use_case = providers.Factory(
        GenerateMetaReportUseCase,
        date_range_service=date_range_service,
        report_service=meta_report_service,
    )
    generate_auto_verdict_use_case = providers.Factory(
        GenerateAutoVerdictUseCase,
        llm_proxy_service=llm_proxy_service,
    )
    ask_dashboard_use_case = providers.Factory(
        AskDashboardUseCase,
        llm_proxy_service=llm_proxy_service,
    )


_container: Container | None = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container


def reset_container() -> None:
    global _container
    _container = None
