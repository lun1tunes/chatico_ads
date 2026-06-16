from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from .container import Container, get_container
from .models.db_helper import db_helper
from .repositories.user import UserRepository

_bearer = HTTPBearer(auto_error=False)


def get_db_session(
    session: AsyncSession = Depends(db_helper.scoped_session_dependency),
) -> AsyncSession:
    return session


def get_di_container() -> Container:
    return get_container()


async def get_current_user(
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
):
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    try:
        payload = container.jwt_service().decode_access_token(credentials.credentials)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token") from exc

    user = await UserRepository(session).get_by_id(str(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def get_client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None
