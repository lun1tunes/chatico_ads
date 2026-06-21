from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from ..repositories.auth_session import AuthSessionRepository
from ..repositories.user import UserRepository
from ..security.jwt_service import JWTService
from ..utils.time import utcnow
from ..models.auth_session import AuthSession
from ..models.user import User


class AuthError(Exception):
    pass


class RegisterUserUseCase:
    def __init__(self, *, session: AsyncSession, password_service, jwt_service: JWTService) -> None:
        self.session = session
        self.password_service = password_service
        self.jwt_service = jwt_service
        self.user_repo = UserRepository(session)
        self.auth_session_repo = AuthSessionRepository(session)

    async def execute(
        self, *, email: str, password: str, locale: str, user_agent: str | None, ip_address: str | None
    ) -> dict[str, object]:
        normalized_email = email.lower().strip()
        if await self.user_repo.get_by_email(normalized_email):
            raise AuthError("A user with this email already exists")

        user = User(
            id=str(uuid4()),
            email=normalized_email,
            password_hash=self.password_service.hash_password(password),
            locale=locale,
        )
        await self.user_repo.create(user)
        tokens = await _issue_tokens(
            session=self.session,
            auth_session_repo=self.auth_session_repo,
            jwt_service=self.jwt_service,
            user=user,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self.session.commit()
        return {"user": user, **tokens}


class LoginUserUseCase:
    def __init__(self, *, session: AsyncSession, password_service, jwt_service: JWTService) -> None:
        self.session = session
        self.password_service = password_service
        self.jwt_service = jwt_service
        self.user_repo = UserRepository(session)
        self.auth_session_repo = AuthSessionRepository(session)

    async def execute(
        self, *, email: str, password: str, user_agent: str | None, ip_address: str | None
    ) -> dict[str, object]:
        normalized_email = email.lower().strip()
        user = await self.user_repo.get_by_email(normalized_email)
        if user is None or not self.password_service.verify_password(password, user.password_hash):
            raise AuthError("Invalid email or password")
        if not user.is_active:
            raise AuthError("User account is inactive")

        tokens = await _issue_tokens(
            session=self.session,
            auth_session_repo=self.auth_session_repo,
            jwt_service=self.jwt_service,
            user=user,
            user_agent=user_agent,
            ip_address=ip_address,
        )
        await self.session.commit()
        return {"user": user, **tokens}


class RefreshSessionUseCase:
    def __init__(self, *, session: AsyncSession, jwt_service: JWTService) -> None:
        self.session = session
        self.jwt_service = jwt_service
        self.user_repo = UserRepository(session)
        self.auth_session_repo = AuthSessionRepository(session)

    async def execute(self, *, refresh_token: str) -> dict[str, object]:
        payload = self.jwt_service.decode_refresh_token(refresh_token)
        session_id = str(payload["sid"])
        auth_session = await self.auth_session_repo.get_active(session_id)
        if auth_session is None:
            raise AuthError("Refresh session not found")
        if auth_session.expires_at <= utcnow():
            raise AuthError("Refresh token expired")
        if auth_session.refresh_token_hash != self.jwt_service.hash_refresh_token(refresh_token):
            raise AuthError("Refresh token does not match active session")

        user = await self.user_repo.get_by_id(str(payload["sub"]))
        if user is None:
            raise AuthError("User not found")

        new_refresh_token = self.jwt_service.create_refresh_token(subject=user.id, session_id=auth_session.id)
        auth_session.refresh_token_hash = self.jwt_service.hash_refresh_token(new_refresh_token)
        auth_session.last_used_at = utcnow()

        await self.session.commit()
        return {
            "user": user,
            "access_token": self.jwt_service.create_access_token(subject=user.id),
            "refresh_token": new_refresh_token,
        }


class LogoutUserUseCase:
    def __init__(self, *, session: AsyncSession, jwt_service: JWTService) -> None:
        self.session = session
        self.jwt_service = jwt_service
        self.auth_session_repo = AuthSessionRepository(session)

    async def execute(self, *, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        try:
            payload = self.jwt_service.decode_refresh_token(refresh_token)
        except Exception:
            return

        auth_session = await self.auth_session_repo.get_active(str(payload["sid"]))
        if auth_session is None:
            return
        auth_session.revoked_at = utcnow()
        await self.session.commit()


class UpdateUserLocaleUseCase:
    def __init__(self, *, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def execute(self, *, user_id: str, locale: str) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise AuthError("User not found")
        if not user.is_active:
            raise AuthError("User account is inactive")

        user.locale = locale
        await self.session.commit()
        return user


async def _issue_tokens(
    *,
    session: AsyncSession,
    auth_session_repo: AuthSessionRepository,
    jwt_service: JWTService,
    user: User,
    user_agent: str | None,
    ip_address: str | None,
) -> dict[str, str]:
    session_id = str(uuid4())
    refresh_token = jwt_service.create_refresh_token(subject=user.id, session_id=session_id)
    auth_session = AuthSession(
        id=session_id,
        user_id=user.id,
        refresh_token_hash=jwt_service.hash_refresh_token(refresh_token),
        user_agent=user_agent,
        ip_address=ip_address,
        expires_at=utcnow() + timedelta(days=jwt_service.refresh_days),
    )
    await auth_session_repo.create(auth_session)
    await session.flush()
    return {
        "access_token": jwt_service.create_access_token(subject=user.id),
        "refresh_token": refresh_token,
    }
