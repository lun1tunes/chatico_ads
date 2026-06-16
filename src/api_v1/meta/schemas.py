from __future__ import annotations

from pydantic import BaseModel


class OAuthStartResponse(BaseModel):
    authorization_url: str


class MetaAdAccountResponse(BaseModel):
    id: str
    external_id: str
    account_id: str
    name: str
    currency: str | None = None
    timezone_name: str | None = None
    account_status: int | None = None
