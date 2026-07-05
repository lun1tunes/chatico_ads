from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.container import Container
from core.dependencies import get_current_user, get_db_session, get_di_container
from core.infrastructure.google_ads_api import GoogleAdsAPIError
from core.infrastructure.meta_graph_api import MetaGraphAPIError
from core.services.google_ads_report_service import GoogleAdsCustomerNotFoundError
from core.services.meta_report_service import MetaAdAccountNotFoundError

router = APIRouter()


@router.get("/meta/ad-accounts/{ad_account_id}/report")
async def get_meta_report(
    ad_account_id: str,
    days: int = Query(default=30, ge=1, le=365),
    force_refresh: bool = Query(default=False),
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        return await container.generate_meta_report_use_case(session=session).execute(
            user_id=user.id,
            ad_account_id=ad_account_id,
            days=days,
            force_refresh=force_refresh,
        )
    except MetaAdAccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetaGraphAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.get("/google-ads/customers/{customer_id}/report")
async def get_google_ads_report(
    customer_id: str,
    days: int = Query(default=30, ge=1, le=365),
    force_refresh: bool = Query(default=False),
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        return await container.generate_google_ads_report_use_case(session=session).execute(
            user_id=user.id,
            customer_id=customer_id,
            days=days,
            force_refresh=force_refresh,
        )
    except GoogleAdsCustomerNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except GoogleAdsAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
