from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.container import Container
from core.dependencies import get_current_user, get_db_session, get_di_container
from .schemas import MetaAdAccountResponse, OAuthStartResponse

router = APIRouter()


@router.get("/oauth/start", response_model=OAuthStartResponse)
async def start_oauth(
    user=Depends(get_current_user),
    container: Container = Depends(get_di_container),
):
    result = await container.build_meta_oauth_url_use_case().execute(user_id=user.id)
    return OAuthStartResponse(**result)


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        await container.handle_meta_oauth_callback_use_case(session=session).execute(code=code, state=state)
        query = urlencode({"provider": "meta", "status": "success"})
    except Exception as exc:  # noqa: BLE001
        query = urlencode({"provider": "meta", "status": "error", "message": str(exc)})
    return RedirectResponse(url=f"{settings.frontend_url}/connections?{query}")


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
