from __future__ import annotations

import logging
from urllib.parse import urlencode

import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.container import Container
from core.dependencies import get_current_user, get_db_session, get_di_container
from core.infrastructure.tiktok_ads_api import TikTokAdsAPIError, TikTokAdsConfigurationError
from core.use_cases.tiktok_ads import TikTokAdsOAuthUseCaseError
from .schemas import OAuthStartResponse, TikTokAdsAdvertiserResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def _connections_redirect_url(*, provider: str, status_value: str, message: str | None = None) -> str:
    query_data = {"provider": provider, "status": status_value}
    if message:
        query_data["message"] = message
    return f"{settings.frontend_url.rstrip('/')}/connections?{urlencode(query_data)}"


async def _rollback_session(session: AsyncSession | None) -> None:
    if session is None:
        return
    try:
        await session.rollback()
    except Exception:  # noqa: BLE001
        logger.exception("Failed to rollback session after TikTok Ads OAuth error")


@router.get("/oauth/start", response_model=OAuthStartResponse)
async def start_oauth(
    user=Depends(get_current_user),
    container: Container = Depends(get_di_container),
):
    try:
        result = await container.build_tiktok_ads_oauth_url_use_case().execute(user_id=user.id)
    except TikTokAdsConfigurationError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return OAuthStartResponse(**result)


@router.get("/oauth/callback")
async def oauth_callback(
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    error_description: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    if error:
        message = error_description or "TikTok Ads access was not granted"
        await _rollback_session(session)
        return RedirectResponse(
            url=_connections_redirect_url(provider="tiktok_ads", status_value="error", message=message)
        )

    if not code or not state:
        await _rollback_session(session)
        return RedirectResponse(
            url=_connections_redirect_url(
                provider="tiktok_ads",
                status_value="error",
                message="Missing TikTok OAuth callback parameters",
            )
        )

    try:
        await container.handle_tiktok_ads_oauth_callback_use_case(session=session).execute(code=code, state=state)
        return RedirectResponse(url=_connections_redirect_url(provider="tiktok_ads", status_value="success"))
    except (TikTokAdsConfigurationError, TikTokAdsAPIError, TikTokAdsOAuthUseCaseError, jwt.InvalidTokenError) as exc:
        await _rollback_session(session)
        logger.warning("TikTok Ads OAuth callback failed: %s", exc)
        return RedirectResponse(
            url=_connections_redirect_url(provider="tiktok_ads", status_value="error", message=str(exc))
        )
    except Exception:  # noqa: BLE001
        await _rollback_session(session)
        logger.exception("Unexpected TikTok Ads OAuth callback failure")
        return RedirectResponse(
            url=_connections_redirect_url(
                provider="tiktok_ads",
                status_value="error",
                message="TikTok Ads connection failed. Please try again.",
            )
        )


@router.get("/advertisers", response_model=list[TikTokAdsAdvertiserResponse])
async def list_advertisers(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    advertisers = await container.list_tiktok_ads_advertisers_use_case(session=session).execute(user_id=user.id)
    return [
        TikTokAdsAdvertiserResponse(
            id=advertiser.id,
            advertiser_id=advertiser.advertiser_id,
            name=advertiser.name,
            currency=advertiser.currency,
            timezone_name=advertiser.timezone_name,
            status=advertiser.status,
        )
        for advertiser in advertisers
    ]


@router.delete("/connections", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_tiktok_ads(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    await container.disconnect_tiktok_ads_use_case(session=session).execute(user_id=user.id)
