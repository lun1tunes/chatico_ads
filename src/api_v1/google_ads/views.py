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
from core.infrastructure.google_ads_api import GoogleAdsAPIError, GoogleAdsConfigurationError
from core.use_cases.google_ads import GoogleAdsOAuthUseCaseError
from .schemas import GoogleAdsCustomerResponse, OAuthStartResponse

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
        logger.exception("Failed to rollback session after Google Ads OAuth error")


@router.get("/oauth/start", response_model=OAuthStartResponse)
async def start_oauth(
    user=Depends(get_current_user),
    container: Container = Depends(get_di_container),
):
    try:
        result = await container.build_google_ads_oauth_url_use_case().execute(user_id=user.id)
    except GoogleAdsConfigurationError as exc:
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
        message = error_description or "Google Ads access was not granted"
        await _rollback_session(session)
        return RedirectResponse(
            url=_connections_redirect_url(provider="google_ads", status_value="error", message=message)
        )

    if not code or not state:
        await _rollback_session(session)
        return RedirectResponse(
            url=_connections_redirect_url(
                provider="google_ads",
                status_value="error",
                message="Missing Google OAuth callback parameters",
            )
        )

    try:
        await container.handle_google_ads_oauth_callback_use_case(session=session).execute(code=code, state=state)
        return RedirectResponse(url=_connections_redirect_url(provider="google_ads", status_value="success"))
    except (GoogleAdsConfigurationError, GoogleAdsAPIError, GoogleAdsOAuthUseCaseError, jwt.InvalidTokenError) as exc:
        await _rollback_session(session)
        logger.warning("Google Ads OAuth callback failed: %s", exc)
        return RedirectResponse(
            url=_connections_redirect_url(provider="google_ads", status_value="error", message=str(exc))
        )
    except Exception:  # noqa: BLE001
        await _rollback_session(session)
        logger.exception("Unexpected Google Ads OAuth callback failure")
        return RedirectResponse(
            url=_connections_redirect_url(
                provider="google_ads",
                status_value="error",
                message="Google Ads connection failed. Please try again.",
            )
        )


@router.get("/customers", response_model=list[GoogleAdsCustomerResponse])
async def list_customers(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    customers = await container.list_google_ads_customers_use_case(session=session).execute(user_id=user.id)
    return [
        GoogleAdsCustomerResponse(
            id=customer.id,
            external_customer_id=customer.external_customer_id,
            resource_name=customer.resource_name,
            descriptive_name=customer.descriptive_name,
            currency_code=customer.currency_code,
            time_zone=customer.time_zone,
            is_manager=customer.is_manager,
            is_directly_accessible=customer.is_directly_accessible,
            hierarchy_level=customer.hierarchy_level,
            root_customer_id=customer.root_customer_id,
            manager_customer_id=customer.manager_customer_id,
            login_customer_id=customer.login_customer_id,
        )
        for customer in customers
    ]


@router.delete("/connections", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_google_ads(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    await container.disconnect_google_ads_use_case(session=session).execute(user_id=user.id)
