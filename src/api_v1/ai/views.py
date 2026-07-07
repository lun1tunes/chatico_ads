from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.container import Container
from core.dependencies import get_current_user, get_db_session, get_di_container
from core.infrastructure.google_ads_api import GoogleAdsAPIError
from core.infrastructure.llm_clients import LLMProxyError
from core.infrastructure.meta_graph_api import MetaGraphAPIError
from core.infrastructure.tiktok_ads_api import TikTokAdsAPIError
from core.services.google_ads_report_service import GoogleAdsCustomerNotFoundError
from core.services.meta_report_service import MetaAdAccountNotFoundError
from core.services.tiktok_ads_report_service import TikTokAdsAdvertiserNotFoundError
from core.utils.ai_context import build_report_context
from .schemas import (
    AutoVerdictRequest,
    ChatRequest,
    ProviderCatalogResponse,
    SaveProviderKeyRequest,
    SavedProviderKeyResponse,
    TextResponse,
)

router = APIRouter()


def _chat_system_prompt(*, report_context: str, language: str) -> str:
    return (
        f"You are an ads analyst assistant. Reply in language code '{language}'. "
        "Use only the provided dashboard context. Answer the user's question directly and keep it short: "
        "maximum 4 concise bullet points or 1 short paragraph, with no intro, no recap, and no filler. "
        "Mention only the most important findings, specific campaign or creative names when relevant, and exactly one next action. "
        "If the data is insufficient, say that briefly.\n\n"
        f"Dashboard context:\n{report_context}"
    )


def _auto_verdict_unavailable_text(language: str) -> str:
    normalized = language.lower().strip()
    if normalized == "kz":
        return "Қысқа қорытынды серверлік AI кілті қосылғаннан кейін қолжетімді болады."
    if normalized == "en":
        return "The quick summary will appear after the server AI key is configured."
    return "Короткий вывод появится после настройки серверного AI-ключа."


def _raise_ai_http_error(exc: Exception) -> None:
    if isinstance(exc, (MetaAdAccountNotFoundError, GoogleAdsCustomerNotFoundError, TikTokAdsAdvertiserNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, (MetaGraphAPIError, GoogleAdsAPIError, TikTokAdsAPIError)):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    if isinstance(exc, LLMProxyError):
        detail = str(exc)
        if detail in {
            "Unsupported AI provider",
            "Add at least one user message before sending the chat request",
            "The last chat message must come from the user",
            "Add an API key or save one for this provider",
            "Saved API key is unreadable, please save it again",
        }:
            status_code = status.HTTP_400_BAD_REQUEST
        elif detail in {"Internal AI summary is not configured", "Internal AI chat is not configured"}:
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        else:
            status_code = status.HTTP_502_BAD_GATEWAY
        raise HTTPException(status_code=status_code, detail=detail) from exc
    raise exc


@router.get("/providers", response_model=list[ProviderCatalogResponse])
async def list_supported_providers(
    container: Container = Depends(get_di_container),
):
    return container.list_supported_ai_providers_use_case().execute()


@router.get("/provider-keys", response_model=list[SavedProviderKeyResponse])
async def list_saved_provider_keys(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        return await container.list_saved_ai_provider_keys_use_case(session=session).execute(user_id=user.id)
    except Exception as exc:  # noqa: BLE001
        _raise_ai_http_error(exc)


@router.put("/provider-keys/{provider}", response_model=SavedProviderKeyResponse)
async def save_provider_key(
    provider: str,
    payload: SaveProviderKeyRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        return await container.save_ai_provider_key_use_case(session=session).execute(
            user_id=user.id,
            provider=provider,
            api_key=payload.api_key,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_ai_http_error(exc)


@router.delete("/provider-keys/{provider}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_provider_key(
    provider: str,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        await container.delete_ai_provider_key_use_case(session=session).execute(
            user_id=user.id,
            provider=provider,
        )
    except Exception as exc:  # noqa: BLE001
        _raise_ai_http_error(exc)


@router.post("/meta/ad-accounts/{ad_account_id}/auto-verdict", response_model=TextResponse)
async def auto_verdict(
    ad_account_id: str,
    payload: AutoVerdictRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        report = await container.generate_meta_report_use_case(session=session).execute(
            user_id=user.id,
            ad_account_id=ad_account_id,
            days=payload.days,
        )
        context = build_report_context(report)
        text = await container.generate_auto_verdict_use_case().execute(
            report_context=context, language=payload.language
        )
        return TextResponse(text=text)
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, LLMProxyError) and str(exc) == "Internal AI summary is not configured":
            return TextResponse(text=_auto_verdict_unavailable_text(payload.language))
        _raise_ai_http_error(exc)


@router.post("/google-ads/customers/{customer_id}/auto-verdict", response_model=TextResponse)
async def google_auto_verdict(
    customer_id: str,
    payload: AutoVerdictRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        report = await container.generate_google_ads_report_use_case(session=session).execute(
            user_id=user.id,
            customer_id=customer_id,
            days=payload.days,
        )
        context = build_report_context(report)
        text = await container.generate_auto_verdict_use_case().execute(
            report_context=context, language=payload.language
        )
        return TextResponse(text=text)
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, LLMProxyError) and str(exc) == "Internal AI summary is not configured":
            return TextResponse(text=_auto_verdict_unavailable_text(payload.language))
        _raise_ai_http_error(exc)


@router.post("/tiktok-ads/advertisers/{advertiser_id}/auto-verdict", response_model=TextResponse)
async def tiktok_auto_verdict(
    advertiser_id: str,
    payload: AutoVerdictRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        report = await container.generate_tiktok_ads_report_use_case(session=session).execute(
            user_id=user.id,
            advertiser_id=advertiser_id,
            days=payload.days,
        )
        context = build_report_context(report)
        text = await container.generate_auto_verdict_use_case().execute(
            report_context=context, language=payload.language
        )
        return TextResponse(text=text)
    except Exception as exc:  # noqa: BLE001
        if isinstance(exc, LLMProxyError) and str(exc) == "Internal AI summary is not configured":
            return TextResponse(text=_auto_verdict_unavailable_text(payload.language))
        _raise_ai_http_error(exc)


@router.post("/meta/ad-accounts/{ad_account_id}/chat", response_model=TextResponse)
async def chat(
    ad_account_id: str,
    payload: ChatRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        report = await container.generate_meta_report_use_case(session=session).execute(
            user_id=user.id,
            ad_account_id=ad_account_id,
            days=payload.days,
        )
        context = build_report_context(report)
        text = await container.ask_dashboard_use_case(session=session).execute(
            user_id=user.id,
            use_client_credentials=payload.use_client_credentials,
            provider=payload.provider,
            api_key=payload.api_key,
            model=payload.model,
            system_prompt=_chat_system_prompt(report_context=context, language=payload.language),
            messages=[message.model_dump() for message in payload.messages],
        )
        return TextResponse(text=text)
    except Exception as exc:  # noqa: BLE001
        _raise_ai_http_error(exc)


@router.post("/google-ads/customers/{customer_id}/chat", response_model=TextResponse)
async def google_chat(
    customer_id: str,
    payload: ChatRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        report = await container.generate_google_ads_report_use_case(session=session).execute(
            user_id=user.id,
            customer_id=customer_id,
            days=payload.days,
        )
        context = build_report_context(report)
        text = await container.ask_dashboard_use_case(session=session).execute(
            user_id=user.id,
            use_client_credentials=payload.use_client_credentials,
            provider=payload.provider,
            api_key=payload.api_key,
            model=payload.model,
            system_prompt=_chat_system_prompt(report_context=context, language=payload.language),
            messages=[message.model_dump() for message in payload.messages],
        )
        return TextResponse(text=text)
    except Exception as exc:  # noqa: BLE001
        _raise_ai_http_error(exc)


@router.post("/tiktok-ads/advertisers/{advertiser_id}/chat", response_model=TextResponse)
async def tiktok_chat(
    advertiser_id: str,
    payload: ChatRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        report = await container.generate_tiktok_ads_report_use_case(session=session).execute(
            user_id=user.id,
            advertiser_id=advertiser_id,
            days=payload.days,
        )
        context = build_report_context(report)
        text = await container.ask_dashboard_use_case(session=session).execute(
            user_id=user.id,
            use_client_credentials=payload.use_client_credentials,
            provider=payload.provider,
            api_key=payload.api_key,
            model=payload.model,
            system_prompt=_chat_system_prompt(report_context=context, language=payload.language),
            messages=[message.model_dump() for message in payload.messages],
        )
        return TextResponse(text=text)
    except Exception as exc:  # noqa: BLE001
        _raise_ai_http_error(exc)
