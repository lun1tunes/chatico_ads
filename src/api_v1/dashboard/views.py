from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.container import Container
from core.dependencies import get_current_user, get_db_session, get_di_container
from core.infrastructure.meta_graph_api import MetaGraphAPIError
from core.services.meta_report_service import MetaAdAccountNotFoundError

router = APIRouter()


@router.get("/meta/ad-accounts/{ad_account_id}/report")
async def get_meta_report(
    ad_account_id: str,
    days: int = Query(default=30, ge=1, le=365),
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        return await container.generate_meta_report_use_case(session=session).execute(
            user_id=user.id,
            ad_account_id=ad_account_id,
            days=days,
        )
    except MetaAdAccountNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except MetaGraphAPIError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
