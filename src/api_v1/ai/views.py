from __future__ import annotations

import logging
import re

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.container import Container
from core.dependencies import get_current_user, get_db_session, get_di_container
from core.infrastructure.google_ads_api import GoogleAdsAPIError
from core.infrastructure.llm_clients import LLMProxyError
from core.infrastructure.meta_graph_api import MetaGraphAPIError
from core.infrastructure.tiktok_ads_api import TikTokAdsAPIError
from core.services.ai_prompt_service import PromptMessageError, PromptTemplateError
from core.services.google_ads_report_service import GoogleAdsCustomerNotFoundError
from core.services.meta_report_service import MetaAdAccountNotFoundError
from core.services.tiktok_ads_report_service import TikTokAdsAdvertiserNotFoundError
from core.utils.ai_context import build_scoped_report_context
from core.utils.auto_verdict_fallback import build_auto_verdict_fallback_text
from .schemas import (
    AutoVerdictRequest,
    ChatRequest,
    ProviderCatalogResponse,
    SaveProviderKeyRequest,
    SavedProviderKeyResponse,
    TextResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)

_AUTO_VERDICT_LIST_LINE_RE = re.compile(r"^([-*+]\s+|\d+\.\s+)")
_AUTO_VERDICT_SENTENCE_END_RE = re.compile(r"[.!?…]$")
_AUTO_VERDICT_WORD_RE = re.compile(r"\S+")
_LATIN_LETTER_RE = re.compile(r"[A-Za-z]")
_CYRILLIC_LETTER_RE = re.compile(r"[А-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүІі]")
_AUTO_VERDICT_MAX_WORDS = 120


def _period_payload_kwargs(payload: AutoVerdictRequest | ChatRequest) -> dict[str, object]:
    return {
        "days": payload.days,
        "since": payload.since,
        "until": payload.until,
    }


def _auto_verdict_unavailable_text(language: str) -> str:
    normalized = language.lower().strip()
    if normalized == "kz":
        return "Қысқа қорытынды серверлік AI кілті қосылғаннан кейін қолжетімді болады."
    if normalized == "en":
        return "The quick summary will appear after the server AI key is configured."
    return "Короткий вывод появится после настройки серверного AI-ключа."


def _auto_verdict_word_count(text: str) -> int:
    return len(_AUTO_VERDICT_WORD_RE.findall(text))


def _truncate_auto_verdict_to_word_limit(text: str, *, word_limit: int = _AUTO_VERDICT_MAX_WORDS) -> str:
    if _auto_verdict_word_count(text) <= word_limit:
        return text

    normalized = text.strip()
    if not normalized:
        return ""

    kept_parts: list[str] = []
    words_kept = 0

    for part in re.split(r"(\s+)", normalized):
        if not part:
            continue
        if part.isspace():
            if kept_parts and not kept_parts[-1].isspace():
                kept_parts.append(part)
            continue
        if words_kept >= word_limit:
            break
        kept_parts.append(part)
        words_kept += 1

    truncated = "".join(kept_parts).strip().rstrip(",;:-")
    if truncated and not _AUTO_VERDICT_SENTENCE_END_RE.search(truncated):
        truncated = truncated.rstrip(".") + "..."
    return truncated


def _auto_verdict_metric_current(report: dict[str, object], key: str) -> float | None:
    summary = report.get("summary")
    if not isinstance(summary, dict):
        return None
    metrics = summary.get("metrics")
    if not isinstance(metrics, dict):
        return None
    metric = metrics.get(key)
    if not isinstance(metric, dict):
        return None
    value = metric.get("current")
    if value is None or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _report_has_no_active_delivery(report: dict[str, object]) -> bool:
    summary = report.get("summary")
    if not isinstance(summary, dict):
        return False

    active_campaigns = summary.get("active_campaigns")
    if active_campaigns is not None and not isinstance(active_campaigns, bool):
        try:
            if float(active_campaigns) <= 0:
                return True
        except (TypeError, ValueError):
            pass

    signals = [
        _auto_verdict_metric_current(report, "spend"),
        _auto_verdict_metric_current(report, "impressions"),
        _auto_verdict_metric_current(report, "clicks"),
        _auto_verdict_metric_current(report, "results"),
    ]
    present_signals = [signal for signal in signals if signal is not None]
    return bool(present_signals) and all(signal <= 0 for signal in present_signals)


def _should_use_auto_verdict_fallback(exc: LLMProxyError) -> bool:
    if exc.status_code in {408, 429, 500, 502, 503, 504}:
        return True

    detail = str(exc).lower()
    retryable_markers = (
        "request failed",
        "timeout",
        "timed out",
        "temporarily unavailable",
        "high demand",
        "service unavailable",
        "did not contain text output",
    )
    return any(marker in detail for marker in retryable_markers)


def _auto_verdict_error_response(
    *,
    exc: Exception,
    payload: AutoVerdictRequest,
    report: dict[str, object] | None,
) -> TextResponse | None:
    if payload.use_client_credentials or not isinstance(exc, LLMProxyError):
        return None

    detail = str(exc)
    if detail == "Internal AI summary is not configured":
        return TextResponse(text=_auto_verdict_unavailable_text(payload.language))
    if report is not None and _should_use_auto_verdict_fallback(exc):
        return TextResponse(
            text=build_auto_verdict_fallback_text(
                report,
                language=payload.language,
                reason="temporary_error",
            )
        )
    return None


def _should_replace_auto_verdict_with_fallback(*, text: str, language: str) -> bool:
    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return True
    if _auto_verdict_word_count(normalized) > _AUTO_VERDICT_MAX_WORDS:
        return True

    blocks = [block.strip() for block in re.split(r"\n\s*\n+", normalized) if block.strip()]
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    has_list_lines = any(_AUTO_VERDICT_LIST_LINE_RE.match(line) for line in lines)

    if len(normalized) < 40:
        return True
    if len(lines) == 1 and len(normalized) < 90 and not _AUTO_VERDICT_SENTENCE_END_RE.search(lines[0]):
        return True
    if len(blocks) == 1 and not has_list_lines and len(normalized) < 110:
        return True

    normalized_language = (language or "ru").strip().lower() or "ru"
    if normalized_language not in {"ru", "kz"}:
        return False

    latin_letters = len(_LATIN_LETTER_RE.findall(normalized))
    cyrillic_letters = len(_CYRILLIC_LETTER_RE.findall(normalized))
    lowered = normalized.lower()
    english_markers = (
        "what works",
        "what underperforms",
        "next action",
        "supporting details",
        "no performance",
        "conclusion",
    )

    if cyrillic_letters == 0 and latin_letters >= 8:
        return True
    if latin_letters >= max(16, cyrillic_letters * 2):
        return True
    if any(marker in lowered for marker in english_markers) and latin_letters >= cyrillic_letters:
        return True

    return False


def _auto_verdict_response_text(*, text: str, report: dict[str, object], payload: AutoVerdictRequest) -> str:
    response_text = text
    if _report_has_no_active_delivery(report) or _should_replace_auto_verdict_with_fallback(
        text=text,
        language=payload.language,
    ):
        response_text = build_auto_verdict_fallback_text(
            report,
            language=payload.language,
            reason="guardrail",
        )
    return _truncate_auto_verdict_to_word_limit(response_text)


def _raise_ai_http_error(exc: Exception) -> None:
    if isinstance(exc, (MetaAdAccountNotFoundError, GoogleAdsCustomerNotFoundError, TikTokAdsAdvertiserNotFoundError)):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, (MetaGraphAPIError, GoogleAdsAPIError, TikTokAdsAPIError)):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    if isinstance(exc, PromptMessageError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if isinstance(exc, PromptTemplateError):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI prompt configuration is invalid",
        ) from exc
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


async def _generate_auto_verdict_text(
    *,
    user_id: str,
    session: AsyncSession,
    container: Container,
    system_prompt: str,
    messages: list[dict[str, str]],
    payload: AutoVerdictRequest,
) -> str:
    return await container.generate_auto_verdict_use_case(session=session).execute(
        user_id=user_id,
        use_client_credentials=payload.use_client_credentials,
        provider=payload.provider,
        api_key=payload.api_key,
        model=payload.model,
        system_prompt=system_prompt,
        messages=messages,
        language=payload.language,
    )


def _report_account_id(report: dict[str, object]) -> str:
    account = report.get("account")
    if not isinstance(account, dict):
        return "unknown"
    for field in ("account_id", "id"):
        value = account.get(field)
        if value is not None and str(value).strip():
            return str(value).strip()
    return "unknown"


def _report_current_period(report: dict[str, object]) -> tuple[str, str]:
    periods = report.get("periods")
    if not isinstance(periods, dict):
        return "unknown", "unknown"
    current = periods.get("current")
    if not isinstance(current, dict):
        return "unknown", "unknown"
    since = str(current.get("since") or "unknown").strip() or "unknown"
    until = str(current.get("until") or "unknown").strip() or "unknown"
    return since, until


def _log_ai_request_prepared(
    *,
    request_type: str,
    platform: str,
    report: dict[str, object],
    prompt_checksums: dict[str, str],
    scope: str | None = None,
) -> None:
    since, until = _report_current_period(report)
    logger.info(
        "AI request prepared type=%s platform=%s account_id=%s report_since=%s report_until=%s scope=%s prompt_checksums=%s",
        request_type,
        platform,
        _report_account_id(report),
        since,
        until,
        scope or "-",
        prompt_checksums,
    )


def _log_ai_prompt_error(
    *,
    request_type: str,
    platform: str,
    report: dict[str, object],
    scope: str | None = None,
) -> None:
    since, until = _report_current_period(report)
    logger.exception(
        "AI prompt assembly failed type=%s platform=%s account_id=%s report_since=%s report_until=%s scope=%s",
        request_type,
        platform,
        _report_account_id(report),
        since,
        until,
        scope or "-",
    )


def _build_auto_verdict_prompt_bundle(
    *,
    container: Container,
    platform: str,
    report: dict[str, object],
    report_context: str,
    language: str,
    scope: str,
):
    try:
        bundle = container.ai_prompt_service().build_auto_verdict_bundle(
            report_context=report_context,
            language=language,
            scope=scope if scope in {"account", "campaign", "ad_group", "creative"} else "account",
        )
    except PromptTemplateError:
        _log_ai_prompt_error(
            request_type="auto_verdict",
            platform=platform,
            report=report,
            scope=scope,
        )
        raise
    _log_ai_request_prepared(
        request_type="auto_verdict",
        platform=platform,
        report=report,
        prompt_checksums=bundle.checksums,
        scope=scope,
    )
    return bundle


def _build_chat_prompt_bundle(
    *,
    container: Container,
    platform: str,
    report: dict[str, object],
    report_context: str,
    language: str,
    messages: list[dict[str, str]],
    scope: str | None = None,
):
    try:
        bundle = container.ai_prompt_service().build_chat_bundle(
            report_context=report_context,
            language=language,
            messages=messages,
        )
    except PromptTemplateError:
        _log_ai_prompt_error(
            request_type="chat",
            platform=platform,
            report=report,
            scope=scope,
        )
        raise
    _log_ai_request_prepared(
        request_type="chat",
        platform=platform,
        report=report,
        prompt_checksums=bundle.checksums,
        scope=scope,
    )
    return bundle


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
    report: dict[str, object] | None = None
    scoped_report: dict[str, object] | None = None
    try:
        report = await container.generate_meta_report_use_case(session=session).execute(
            user_id=user.id,
            ad_account_id=ad_account_id,
            **_period_payload_kwargs(payload),
        )
        context, effective_scope, scoped_report = build_scoped_report_context(
            report,
            scope=payload.scope,
            campaign_id=payload.campaign_id,
            ad_group_id=payload.ad_group_id,
            creative_id=payload.creative_id,
        )
        prompt_bundle = _build_auto_verdict_prompt_bundle(
            container=container,
            platform="meta",
            report=scoped_report or report,
            report_context=context,
            language=payload.language,
            scope=effective_scope,
        )
        text = await _generate_auto_verdict_text(
            user_id=user.id,
            session=session,
            container=container,
            system_prompt=prompt_bundle.system_prompt,
            messages=prompt_bundle.messages,
            payload=payload,
        )
        return TextResponse(text=_auto_verdict_response_text(text=text, report=scoped_report, payload=payload))
    except Exception as exc:  # noqa: BLE001
        fallback_response = _auto_verdict_error_response(exc=exc, payload=payload, report=scoped_report or report)
        if fallback_response is not None:
            return fallback_response
        _raise_ai_http_error(exc)


@router.post("/google-ads/customers/{customer_id}/auto-verdict", response_model=TextResponse)
async def google_auto_verdict(
    customer_id: str,
    payload: AutoVerdictRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    report: dict[str, object] | None = None
    scoped_report: dict[str, object] | None = None
    try:
        report = await container.generate_google_ads_report_use_case(session=session).execute(
            user_id=user.id,
            customer_id=customer_id,
            **_period_payload_kwargs(payload),
        )
        context, effective_scope, scoped_report = build_scoped_report_context(
            report,
            scope=payload.scope,
            campaign_id=payload.campaign_id,
            ad_group_id=payload.ad_group_id,
            creative_id=payload.creative_id,
        )
        prompt_bundle = _build_auto_verdict_prompt_bundle(
            container=container,
            platform="google_ads",
            report=scoped_report or report,
            report_context=context,
            language=payload.language,
            scope=effective_scope,
        )
        text = await _generate_auto_verdict_text(
            user_id=user.id,
            session=session,
            container=container,
            system_prompt=prompt_bundle.system_prompt,
            messages=prompt_bundle.messages,
            payload=payload,
        )
        return TextResponse(text=_auto_verdict_response_text(text=text, report=scoped_report, payload=payload))
    except Exception as exc:  # noqa: BLE001
        fallback_response = _auto_verdict_error_response(exc=exc, payload=payload, report=scoped_report or report)
        if fallback_response is not None:
            return fallback_response
        _raise_ai_http_error(exc)


@router.post("/tiktok-ads/advertisers/{advertiser_id}/auto-verdict", response_model=TextResponse)
async def tiktok_auto_verdict(
    advertiser_id: str,
    payload: AutoVerdictRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    report: dict[str, object] | None = None
    scoped_report: dict[str, object] | None = None
    try:
        report = await container.generate_tiktok_ads_report_use_case(session=session).execute(
            user_id=user.id,
            advertiser_id=advertiser_id,
            **_period_payload_kwargs(payload),
        )
        context, effective_scope, scoped_report = build_scoped_report_context(
            report,
            scope=payload.scope,
            campaign_id=payload.campaign_id,
            ad_group_id=payload.ad_group_id,
            creative_id=payload.creative_id,
        )
        prompt_bundle = _build_auto_verdict_prompt_bundle(
            container=container,
            platform="tiktok_ads",
            report=scoped_report or report,
            report_context=context,
            language=payload.language,
            scope=effective_scope,
        )
        text = await _generate_auto_verdict_text(
            user_id=user.id,
            session=session,
            container=container,
            system_prompt=prompt_bundle.system_prompt,
            messages=prompt_bundle.messages,
            payload=payload,
        )
        return TextResponse(text=_auto_verdict_response_text(text=text, report=scoped_report, payload=payload))
    except Exception as exc:  # noqa: BLE001
        fallback_response = _auto_verdict_error_response(exc=exc, payload=payload, report=scoped_report or report)
        if fallback_response is not None:
            return fallback_response
        _raise_ai_http_error(exc)


@router.post("/meta/ad-accounts/{ad_account_id}/chat", response_model=TextResponse)
async def chat(
    ad_account_id: str,
    payload: ChatRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    report: dict[str, object] | None = None
    scoped_report: dict[str, object] | None = None
    try:
        report = await container.generate_meta_report_use_case(session=session).execute(
            user_id=user.id,
            ad_account_id=ad_account_id,
            **_period_payload_kwargs(payload),
        )
        context, effective_scope, scoped_report = build_scoped_report_context(
            report,
            scope=payload.scope,
            campaign_id=payload.campaign_id,
            ad_group_id=payload.ad_group_id,
            creative_id=payload.creative_id,
        )
        prompt_bundle = _build_chat_prompt_bundle(
            container=container,
            platform="meta",
            report=scoped_report or report,
            report_context=context,
            language=payload.language,
            messages=[message.model_dump() for message in payload.messages],
            scope=effective_scope,
        )
        text = await container.ask_dashboard_use_case(session=session).execute(
            user_id=user.id,
            use_client_credentials=payload.use_client_credentials,
            provider=payload.provider,
            api_key=payload.api_key,
            model=payload.model,
            system_prompt=prompt_bundle.system_prompt,
            messages=prompt_bundle.messages,
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
    report: dict[str, object] | None = None
    scoped_report: dict[str, object] | None = None
    try:
        report = await container.generate_google_ads_report_use_case(session=session).execute(
            user_id=user.id,
            customer_id=customer_id,
            **_period_payload_kwargs(payload),
        )
        context, effective_scope, scoped_report = build_scoped_report_context(
            report,
            scope=payload.scope,
            campaign_id=payload.campaign_id,
            ad_group_id=payload.ad_group_id,
            creative_id=payload.creative_id,
        )
        prompt_bundle = _build_chat_prompt_bundle(
            container=container,
            platform="google_ads",
            report=scoped_report or report,
            report_context=context,
            language=payload.language,
            messages=[message.model_dump() for message in payload.messages],
            scope=effective_scope,
        )
        text = await container.ask_dashboard_use_case(session=session).execute(
            user_id=user.id,
            use_client_credentials=payload.use_client_credentials,
            provider=payload.provider,
            api_key=payload.api_key,
            model=payload.model,
            system_prompt=prompt_bundle.system_prompt,
            messages=prompt_bundle.messages,
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
    report: dict[str, object] | None = None
    scoped_report: dict[str, object] | None = None
    try:
        report = await container.generate_tiktok_ads_report_use_case(session=session).execute(
            user_id=user.id,
            advertiser_id=advertiser_id,
            **_period_payload_kwargs(payload),
        )
        context, effective_scope, scoped_report = build_scoped_report_context(
            report,
            scope=payload.scope,
            campaign_id=payload.campaign_id,
            ad_group_id=payload.ad_group_id,
            creative_id=payload.creative_id,
        )
        prompt_bundle = _build_chat_prompt_bundle(
            container=container,
            platform="tiktok_ads",
            report=scoped_report or report,
            report_context=context,
            language=payload.language,
            messages=[message.model_dump() for message in payload.messages],
            scope=effective_scope,
        )
        text = await container.ask_dashboard_use_case(session=session).execute(
            user_id=user.id,
            use_client_credentials=payload.use_client_credentials,
            provider=payload.provider,
            api_key=payload.api_key,
            model=payload.model,
            system_prompt=prompt_bundle.system_prompt,
            messages=prompt_bundle.messages,
        )
        return TextResponse(text=text)
    except Exception as exc:  # noqa: BLE001
        _raise_ai_http_error(exc)
