from __future__ import annotations

import logging
from urllib.parse import urlencode

import jwt
from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.container import Container
from core.dependencies import get_current_user, get_db_session, get_di_container
from core.infrastructure.meta_graph_api import MetaGraphAPIError
from .schemas import MetaAdAccountResponse, OAuthStartResponse

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
        logger.exception("Failed to rollback session after Meta OAuth error")


@router.get("/oauth/start", response_model=OAuthStartResponse)
async def start_oauth(
    user=Depends(get_current_user),
    container: Container = Depends(get_di_container),
):
    result = await container.build_meta_oauth_url_use_case().execute(user_id=user.id)
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
        message = error_description or "Meta access was not granted"
        await _rollback_session(session)
        return RedirectResponse(url=_connections_redirect_url(provider="meta", status_value="error", message=message))

    if not code or not state:
        await _rollback_session(session)
        return RedirectResponse(
            url=_connections_redirect_url(
                provider="meta",
                status_value="error",
                message="Missing Meta OAuth callback parameters",
            )
        )

    try:
        await container.handle_meta_oauth_callback_use_case(session=session).execute(code=code, state=state)
        return RedirectResponse(url=_connections_redirect_url(provider="meta", status_value="success"))
    except (MetaGraphAPIError, jwt.InvalidTokenError) as exc:
        await _rollback_session(session)
        logger.warning("Meta OAuth callback failed: %s", exc)
        return RedirectResponse(url=_connections_redirect_url(provider="meta", status_value="error", message=str(exc)))
    except Exception:  # noqa: BLE001
        await _rollback_session(session)
        logger.exception("Unexpected Meta OAuth callback failure")
        return RedirectResponse(
            url=_connections_redirect_url(
                provider="meta",
                status_value="error",
                message="Meta connection failed. Please try again.",
            )
        )


@router.get("/ad-accounts", response_model=list[MetaAdAccountResponse])
async def list_ad_accounts(
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    accounts = await container.list_meta_ad_accounts_use_case(session=session).execute(user_id=user.id)
    return [
        MetaAdAccountResponse(
            id=account.id,
            external_id=account.external_id,
            account_id=account.account_id,
            name=account.name,
            currency=account.currency,
            timezone_name=account.timezone_name,
            account_status=account.account_status,
        )
        for account in accounts
    ]
