from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.container import Container
from core.dependencies import get_current_user, get_db_session, get_di_container
from core.infrastructure.llm_clients import LLMProxyError
from core.infrastructure.meta_graph_api import MetaGraphAPIError
from core.services.meta_report_service import MetaAdAccountNotFoundError
from core.utils.ai_context import build_report_context
from .schemas import AutoVerdictRequest, ChatRequest, TextResponse

router = APIRouter()


def _chat_system_prompt(*, report_context: str, language: str) -> str:
    return (
        f"You are an ads analyst assistant. Reply in language code '{language}'. "
        "Use only the provided dashboard context and be concrete about campaigns, creatives, spend efficiency, and next actions.\n\n"
        f"Dashboard context:\n{report_context}"
    )


def _raise_ai_http_error(exc: Exception) -> None:
    if isinstance(exc, MetaAdAccountNotFoundError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    if isinstance(exc, MetaGraphAPIError):
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    if isinstance(exc, LLMProxyError):
        status_code = status.HTTP_400_BAD_REQUEST if "Unsupported AI provider" in str(exc) else status.HTTP_502_BAD_GATEWAY
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
    raise exc


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
        text = await container.generate_auto_verdict_use_case().execute(report_context=context, language=payload.language)
        return TextResponse(text=text)
    except Exception as exc:  # noqa: BLE001
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
        text = await container.ask_dashboard_use_case().execute(
            provider=payload.provider,
            api_key=payload.api_key,
            model=payload.model,
            system_prompt=_chat_system_prompt(report_context=context, language=payload.language),
            messages=[message.model_dump() for message in payload.messages],
        )
        return TextResponse(text=text)
    except Exception as exc:  # noqa: BLE001
        _raise_ai_http_error(exc)
