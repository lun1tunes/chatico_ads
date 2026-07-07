from __future__ import annotations

from dependency_injector import containers, providers

from .infrastructure.google_ads_api import GoogleAdsAPIClient
from .infrastructure.llm_clients import AnthropicClient, GeminiClient, OpenAIClient
from .infrastructure.meta_graph_api import MetaGraphAPIClient
from .infrastructure.tiktok_ads_api import TikTokAdsAPIClient
from .infrastructure.public_media_preview import PublicCreativePreviewClient
from .config import settings
from .security.encryption_service import EncryptionService
from .security.jwt_service import JWTService
from .security.password_service import PasswordService
from .services.date_range_service import DateRangeService
from .services.google_ads_state_service import GoogleAdsOAuthStateService
from .services.google_ads_report_service import GoogleAdsReportService
from .services.llm_proxy_service import LLMProxyService
from .services.meta_report_service import MetaReportService
from .services.meta_signed_request_service import MetaSignedRequestService
from .services.meta_state_service import MetaOAuthStateService
from .services.tiktok_ads_report_service import TikTokAdsReportService
from .services.tiktok_ads_state_service import TikTokAdsOAuthStateService
from .use_cases.auth import LoginUserUseCase, LogoutUserUseCase, RefreshSessionUseCase, RegisterUserUseCase
from .use_cases.auth import UpdateUserLocaleUseCase
from .use_cases.dashboard import (
    AskDashboardUseCase,
    DeleteAIProviderKeyUseCase,
    GenerateAutoVerdictUseCase,
    GenerateGoogleAdsReportUseCase,
    GenerateMetaReportUseCase,
    GenerateTikTokAdsReportUseCase,
    ListSavedAIProviderKeysUseCase,
    ListSupportedAIProvidersUseCase,
    SaveAIProviderKeyUseCase,
)
from .use_cases.google_ads import (
    BuildGoogleAdsOAuthUrlUseCase,
    DisconnectGoogleAdsUseCase,
    HandleGoogleAdsOAuthCallbackUseCase,
    ListGoogleAdsCustomersUseCase,
)
from .use_cases.meta_data_deletion import GetMetaDataDeletionStatusUseCase, HandleMetaDataDeletionCallbackUseCase
from .use_cases.meta import (
    BuildMetaOAuthUrlUseCase,
    DisconnectMetaUseCase,
    HandleMetaOAuthCallbackUseCase,
    ListMetaAdAccountsUseCase,
)
from .use_cases.tiktok_ads import (
    BuildTikTokAdsOAuthUrlUseCase,
    DisconnectTikTokAdsUseCase,
    HandleTikTokAdsOAuthCallbackUseCase,
    ListTikTokAdsAdvertisersUseCase,
)


class Container(containers.DeclarativeContainer):
    password_service = providers.Singleton(PasswordService)
    encryption_service = providers.Singleton(EncryptionService)
    jwt_service = providers.Singleton(JWTService)
    meta_state_service = providers.Singleton(MetaOAuthStateService)
    meta_signed_request_service = providers.Singleton(MetaSignedRequestService)
    google_ads_state_service = providers.Singleton(GoogleAdsOAuthStateService)
    tiktok_ads_state_service = providers.Singleton(TikTokAdsOAuthStateService)
    date_range_service = providers.Singleton(DateRangeService)

    meta_client = providers.Singleton(MetaGraphAPIClient)
    google_ads_client = providers.Singleton(GoogleAdsAPIClient)
    tiktok_ads_client = providers.Singleton(TikTokAdsAPIClient)
    creative_preview_client = providers.Singleton(PublicCreativePreviewClient)
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
        preview_client=creative_preview_client,
        cache_ttl_seconds=settings.meta_report_cache_ttl_seconds,
        snapshot_cache_ttl_seconds=settings.meta_report_snapshot_ttl_seconds,
    )
    google_ads_report_service = providers.Singleton(
        GoogleAdsReportService,
        google_ads_client=google_ads_client,
        encryption_service=encryption_service,
        cache_ttl_seconds=settings.meta_report_cache_ttl_seconds,
    )
    tiktok_ads_report_service = providers.Singleton(
        TikTokAdsReportService,
        tiktok_ads_client=tiktok_ads_client,
        encryption_service=encryption_service,
        cache_ttl_seconds=settings.meta_report_cache_ttl_seconds,
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
    update_user_locale_use_case = providers.Factory(UpdateUserLocaleUseCase)

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
    disconnect_meta_use_case = providers.Factory(
        DisconnectMetaUseCase,
        report_service=meta_report_service,
    )
    handle_meta_data_deletion_callback_use_case = providers.Factory(
        HandleMetaDataDeletionCallbackUseCase,
        signed_request_service=meta_signed_request_service,
    )
    get_meta_data_deletion_status_use_case = providers.Factory(GetMetaDataDeletionStatusUseCase)
    build_google_ads_oauth_url_use_case = providers.Factory(
        BuildGoogleAdsOAuthUrlUseCase,
        state_service=google_ads_state_service,
        google_ads_client=google_ads_client,
    )
    handle_google_ads_oauth_callback_use_case = providers.Factory(
        HandleGoogleAdsOAuthCallbackUseCase,
        state_service=google_ads_state_service,
        google_ads_client=google_ads_client,
        encryption_service=encryption_service,
    )
    list_google_ads_customers_use_case = providers.Factory(ListGoogleAdsCustomersUseCase)
    disconnect_google_ads_use_case = providers.Factory(
        DisconnectGoogleAdsUseCase,
        report_service=google_ads_report_service,
    )
    build_tiktok_ads_oauth_url_use_case = providers.Factory(
        BuildTikTokAdsOAuthUrlUseCase,
        state_service=tiktok_ads_state_service,
        tiktok_ads_client=tiktok_ads_client,
    )
    handle_tiktok_ads_oauth_callback_use_case = providers.Factory(
        HandleTikTokAdsOAuthCallbackUseCase,
        state_service=tiktok_ads_state_service,
        tiktok_ads_client=tiktok_ads_client,
        encryption_service=encryption_service,
    )
    list_tiktok_ads_advertisers_use_case = providers.Factory(ListTikTokAdsAdvertisersUseCase)
    disconnect_tiktok_ads_use_case = providers.Factory(
        DisconnectTikTokAdsUseCase,
        report_service=tiktok_ads_report_service,
    )

    generate_meta_report_use_case = providers.Factory(
        GenerateMetaReportUseCase,
        date_range_service=date_range_service,
        report_service=meta_report_service,
    )
    generate_google_ads_report_use_case = providers.Factory(
        GenerateGoogleAdsReportUseCase,
        date_range_service=date_range_service,
        report_service=google_ads_report_service,
    )
    generate_tiktok_ads_report_use_case = providers.Factory(
        GenerateTikTokAdsReportUseCase,
        date_range_service=date_range_service,
        report_service=tiktok_ads_report_service,
    )
    generate_auto_verdict_use_case = providers.Factory(
        GenerateAutoVerdictUseCase,
        llm_proxy_service=llm_proxy_service,
    )
    list_supported_ai_providers_use_case = providers.Factory(
        ListSupportedAIProvidersUseCase,
        llm_proxy_service=llm_proxy_service,
    )
    list_saved_ai_provider_keys_use_case = providers.Factory(ListSavedAIProviderKeysUseCase)
    save_ai_provider_key_use_case = providers.Factory(
        SaveAIProviderKeyUseCase,
        encryption_service=encryption_service,
        llm_proxy_service=llm_proxy_service,
    )
    delete_ai_provider_key_use_case = providers.Factory(
        DeleteAIProviderKeyUseCase,
        llm_proxy_service=llm_proxy_service,
    )
    ask_dashboard_use_case = providers.Factory(
        AskDashboardUseCase,
        llm_proxy_service=llm_proxy_service,
        encryption_service=encryption_service,
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
