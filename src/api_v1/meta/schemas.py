from __future__ import annotations

from datetime import datetime

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


class MetaAdAccountRefreshResponse(BaseModel):
    refreshed_connections: int
    connected_accounts: int
    added_accounts: int
    updated_accounts: int
    removed_accounts: int


class MetaDataDeletionCallbackResponse(BaseModel):
    url: str
    confirmation_code: str


class MetaDataDeletionStatusResponse(BaseModel):
    confirmation_code: str
    status: str
    detail: str
    deleted_users_count: int
    requested_at: datetime
    completed_at: datetime | None = None
