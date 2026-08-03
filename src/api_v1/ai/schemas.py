from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

AutoVerdictScope = Literal["account", "campaign", "ad_group", "creative"]


class PeriodSelectionRequest(BaseModel):
    days: int = Field(default=30, ge=1, le=365)
    since: date | None = None
    until: date | None = None

    @model_validator(mode="after")
    def validate_period(self) -> "PeriodSelectionRequest":
        if self.since is None and self.until is None:
            return self
        if self.since is None or self.until is None:
            raise ValueError("since and until must be provided together")
        if self.until < self.since:
            raise ValueError("until must be on or after since")
        if (self.until - self.since).days + 1 > 365:
            raise ValueError("custom period cannot exceed 365 days")
        return self


class AutoVerdictRequest(PeriodSelectionRequest):
    language: str = Field(default="ru", min_length=2, max_length=8)
    use_client_credentials: bool = False
    scope: AutoVerdictScope = "account"
    campaign_id: str | None = Field(default=None, min_length=1, max_length=128)
    ad_group_id: str | None = Field(default=None, min_length=1, max_length=128)
    creative_id: str | None = Field(default=None, min_length=1, max_length=128)
    provider: str | None = None
    api_key: str | None = Field(default=None, min_length=10, max_length=512)
    model: str | None = None


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(PeriodSelectionRequest):
    language: str = Field(default="ru", min_length=2, max_length=8)
    use_client_credentials: bool = False
    scope: AutoVerdictScope = "account"
    campaign_id: str | None = Field(default=None, min_length=1, max_length=128)
    ad_group_id: str | None = Field(default=None, min_length=1, max_length=128)
    creative_id: str | None = Field(default=None, min_length=1, max_length=128)
    provider: str | None = None
    api_key: str | None = Field(default=None, min_length=10, max_length=512)
    model: str | None = None
    messages: list[ChatMessage]


class SaveProviderKeyRequest(BaseModel):
    api_key: str = Field(min_length=10, max_length=512)


class ProviderModelPresetResponse(BaseModel):
    value: str
    label: str
    is_default: bool = False


class ProviderCatalogResponse(BaseModel):
    key: str
    label: str
    default_model: str
    presets: list[ProviderModelPresetResponse]
    supports_custom_model: bool = True


class SavedProviderKeyResponse(BaseModel):
    provider: str
    has_saved_key: bool = True
    updated_at: datetime


class TextResponse(BaseModel):
    text: str
