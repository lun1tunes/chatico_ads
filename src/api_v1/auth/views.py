from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.container import Container
from core.dependencies import get_current_user, get_db_session, get_di_container, get_client_ip
from core.use_cases.auth import AuthError
from .schemas import AuthResponse, LoginRequest, RegisterRequest, UpdateLocaleRequest, UserResponse

router = APIRouter()

_LEGACY_REFRESH_COOKIE_NAME = "refresh_token"


def _refresh_cookie_clearance_targets() -> set[tuple[str, str]]:
    current_name = settings.auth.refresh_cookie_name
    current_path = settings.auth.refresh_cookie_path
    targets = {(current_name, current_path), (current_name, "/")}

    if current_path == "/":
        targets.add((_LEGACY_REFRESH_COOKIE_NAME, "/"))
    else:
        targets.add((_LEGACY_REFRESH_COOKIE_NAME, current_path))

    return targets


def _purge_refresh_cookies(response: Response) -> None:
    for cookie_name, cookie_path in _refresh_cookie_clearance_targets():
        response.delete_cookie(key=cookie_name, path=cookie_path)


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    _purge_refresh_cookies(response)
    response.set_cookie(
        key=settings.auth.refresh_cookie_name,
        value=refresh_token,
        httponly=True,
        secure=settings.auth.refresh_cookie_secure,
        samesite=settings.auth.refresh_cookie_samesite,
        max_age=settings.auth.refresh_token_days * 24 * 60 * 60,
        path=settings.auth.refresh_cookie_path,
    )


def _clear_refresh_cookie(response: Response) -> None:
    _purge_refresh_cookies(response)


def _serialize_user(user) -> UserResponse:
    return UserResponse(id=user.id, email=user.email, locale=user.locale, is_active=user.is_active)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        result = await container.register_user_use_case(session=session).execute(
            email=payload.email,
            password=payload.password,
            locale=payload.locale,
            user_agent=request.headers.get("user-agent"),
            ip_address=get_client_ip(request),
        )
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    _set_refresh_cookie(response, result["refresh_token"])
    return AuthResponse(access_token=result["access_token"], user=_serialize_user(result["user"]))


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        result = await container.login_user_use_case(session=session).execute(
            email=payload.email,
            password=payload.password,
            user_agent=request.headers.get("user-agent"),
            ip_address=get_client_ip(request),
        )
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    _set_refresh_cookie(response, result["refresh_token"])
    return AuthResponse(access_token=result["access_token"], user=_serialize_user(result["user"]))


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    refresh_token = request.cookies.get(settings.auth.refresh_cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token cookie is missing")

    try:
        result = await container.refresh_session_use_case(session=session).execute(refresh_token=refresh_token)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is invalid") from exc

    _set_refresh_cookie(response, result["refresh_token"])
    return AuthResponse(access_token=result["access_token"], user=_serialize_user(result["user"]))


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    await container.logout_user_use_case(session=session).execute(
        refresh_token=request.cookies.get(settings.auth.refresh_cookie_name)
    )
    _clear_refresh_cookie(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)):
    return _serialize_user(user)


@router.patch("/me/locale", response_model=UserResponse)
async def update_locale(
    payload: UpdateLocaleRequest,
    user=Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: Container = Depends(get_di_container),
):
    try:
        updated_user = await container.update_user_locale_use_case(session=session).execute(
            user_id=user.id,
            locale=payload.locale,
        )
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _serialize_user(updated_user)
