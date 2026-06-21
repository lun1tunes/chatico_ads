from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt

from ..config import settings


class GoogleAdsOAuthStateService:
    def create_state_token(self, *, user_id: str) -> str:
        now = datetime.now(timezone.utc)
        payload = {
            "sub": user_id,
            "type": "google_ads_oauth_state",
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=10)).timestamp()),
        }
        return jwt.encode(payload, settings.auth.secret_key, algorithm=settings.auth.algorithm)

    def decode_state_token(self, state: str) -> dict[str, str]:
        payload = jwt.decode(state, settings.auth.secret_key, algorithms=[settings.auth.algorithm])
        if payload.get("type") != "google_ads_oauth_state":
            raise jwt.InvalidTokenError("Invalid OAuth state token")
        return payload
