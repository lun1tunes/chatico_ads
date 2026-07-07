from __future__ import annotations

from pydantic import BaseModel


class OAuthStartResponse(BaseModel):
    authorization_url: str


class TikTokAdsAdvertiserResponse(BaseModel):
    id: str
    advertiser_id: str
    name: str
    currency: str | None = None
    timezone_name: str | None = None
    status: str | None = None
