from __future__ import annotations

from pydantic import BaseModel


class OAuthStartResponse(BaseModel):
    authorization_url: str


class GoogleAdsCustomerResponse(BaseModel):
    id: str
    external_customer_id: str
    resource_name: str
    descriptive_name: str
    currency_code: str | None = None
    time_zone: str | None = None
    is_manager: bool
    is_directly_accessible: bool
    hierarchy_level: int
    root_customer_id: str | None = None
    manager_customer_id: str | None = None
    login_customer_id: str | None = None
