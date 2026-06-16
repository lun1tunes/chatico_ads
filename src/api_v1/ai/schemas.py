from __future__ import annotations

from pydantic import BaseModel, Field


class AutoVerdictRequest(BaseModel):
    days: int = Field(default=30, ge=1, le=365)
    language: str = Field(default="ru", min_length=2, max_length=8)


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    days: int = Field(default=30, ge=1, le=365)
    language: str = Field(default="ru", min_length=2, max_length=8)
    provider: str = Field(default="anthropic")
    api_key: str = Field(min_length=10, max_length=512)
    model: str | None = None
    messages: list[ChatMessage]


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


class TextResponse(BaseModel):
    text: str
