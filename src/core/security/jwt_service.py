from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from uuid import uuid4

import jwt

from ..config import settings


class JWTService:
    def __init__(
        self,
        *,
        secret_key: str | None = None,
        algorithm: str | None = None,
        access_minutes: int | None = None,
        refresh_days: int | None = None,
    ) -> None:
        self.secret_key = secret_key or settings.auth.secret_key
        self.algorithm = algorithm or settings.auth.algorithm
        self.access_minutes = access_minutes or settings.auth.access_token_minutes
        self.refresh_days = refresh_days or settings.auth.refresh_token_days

    def create_access_token(self, *, subject: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "type": "access",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=self.access_minutes)).timestamp()),
            "jti": uuid4().hex,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(self, *, subject: str, session_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": subject,
            "sid": session_id,
            "type": "refresh",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(days=self.refresh_days)).timestamp()),
            "jti": uuid4().hex,
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_access_token(self, token: str) -> dict[str, str]:
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        if payload.get("type") != "access":
            raise jwt.InvalidTokenError("Invalid access token type")
        return payload

    def decode_refresh_token(self, token: str) -> dict[str, str]:
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        if payload.get("type") != "refresh":
            raise jwt.InvalidTokenError("Invalid refresh token type")
        return payload

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        return sha256(token.encode()).hexdigest()
