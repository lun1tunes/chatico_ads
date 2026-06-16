from __future__ import annotations

from functools import cached_property
from typing import Annotated, Self

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


class AuthSettings(BaseModel):
    secret_key: str
    algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    refresh_cookie_name: str = "refresh_token"
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: str = "lax"

    @model_validator(mode="after")
    def validate_values(self) -> Self:
        if not self.secret_key.strip():
            raise ValueError("JWT_SECRET_KEY must be set")
        self.access_token_minutes = max(5, int(self.access_token_minutes))
        self.refresh_token_days = max(1, int(self.refresh_token_days))
        self.refresh_cookie_samesite = self.refresh_cookie_samesite.lower()
        if self.refresh_cookie_samesite not in {"lax", "strict", "none"}:
            self.refresh_cookie_samesite = "lax"
        return self


class MetaSettings(BaseModel):
    app_id: str
    app_secret: str
    graph_version: str = "v24.0"
    oauth_redirect_uri: str
    oauth_scopes: list[str] = Field(default_factory=lambda: ["ads_read", "ads_management", "business_management"])
    oauth_config_id: str | None = None
    exchange_long_lived_token: bool = True

    @field_validator("oauth_scopes", mode="before")
    @classmethod
    def normalize_scopes(cls, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return _csv(value)
        return ["ads_read", "ads_management", "business_management"]

    @model_validator(mode="after")
    def validate_values(self) -> Self:
        if not self.app_id.strip():
            raise ValueError("META_APP_ID must be set")
        if not self.app_secret.strip():
            raise ValueError("META_APP_SECRET must be set")
        if not self.oauth_redirect_uri.strip():
            raise ValueError("META_OAUTH_REDIRECT_URI must be set")
        if not self.graph_version.startswith("v"):
            self.graph_version = f"v{self.graph_version}"
        return self


class LLMSettings(BaseModel):
    anthropic_api_key: str
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_version: str = "2023-06-01"
    openai_default_model: str = "gpt-5-mini"
    gemini_default_model: str = "gemini-3.5-flash"
    max_tokens: int = 1200

    @model_validator(mode="after")
    def validate_values(self) -> Self:
        if not self.anthropic_api_key.strip():
            raise ValueError("INTERNAL_ANTHROPIC_API_KEY must be set")
        self.max_tokens = max(256, int(self.max_tokens))
        return self


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "Chatico Ads"
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://postgres:postgres@postgres:5432/chatico_ads"
    frontend_url: str = "http://localhost:4173"
    jwt_secret_key: str = Field(validation_alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 30
    refresh_cookie_name: str = "refresh_token"
    refresh_cookie_secure: bool = False
    refresh_cookie_samesite: str = "lax"
    meta_app_id: str = Field(validation_alias="META_APP_ID")
    meta_app_secret: str = Field(validation_alias="META_APP_SECRET")
    meta_graph_version: str = "v24.0"
    meta_oauth_redirect_uri: str = Field(validation_alias="META_OAUTH_REDIRECT_URI")
    meta_oauth_scopes: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["ads_read", "ads_management", "business_management"]
    )
    meta_oauth_config_id: str | None = None
    meta_exchange_long_lived_token: bool = True
    internal_anthropic_api_key: str = Field(validation_alias="INTERNAL_ANTHROPIC_API_KEY")
    internal_anthropic_model: str = "claude-sonnet-4-6"
    anthropic_version: str = "2023-06-01"
    openai_default_model: str = "gpt-5-mini"
    gemini_default_model: str = "gemini-3.5-flash"
    llm_max_tokens: int = 1200
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:4173", "http://localhost:5173"],
    )
    field_encryption_key: str = Field(validation_alias="FIELD_ENCRYPTION_KEY")

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def normalize_origins(cls, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return _csv(value)
        return ["http://localhost:4173", "http://localhost:5173"]

    @field_validator("meta_oauth_scopes", mode="before")
    @classmethod
    def normalize_scopes(cls, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return _csv(value)
        return ["ads_read", "ads_management", "business_management"]

    @model_validator(mode="after")
    def validate_values(self) -> Self:
        if not self.field_encryption_key.strip():
            raise ValueError("FIELD_ENCRYPTION_KEY must be set")
        if not self.jwt_secret_key.strip():
            raise ValueError("JWT_SECRET_KEY must be set")
        if not self.meta_app_id.strip():
            raise ValueError("META_APP_ID must be set")
        if not self.meta_app_secret.strip():
            raise ValueError("META_APP_SECRET must be set")
        if not self.meta_oauth_redirect_uri.strip():
            raise ValueError("META_OAUTH_REDIRECT_URI must be set")
        if not self.internal_anthropic_api_key.strip():
            raise ValueError("INTERNAL_ANTHROPIC_API_KEY must be set")
        return self

    @cached_property
    def auth(self) -> AuthSettings:
        return AuthSettings(
            secret_key=self.jwt_secret_key,
            algorithm=self.jwt_algorithm,
            access_token_minutes=self.access_token_minutes,
            refresh_token_days=self.refresh_token_days,
            refresh_cookie_name=self.refresh_cookie_name,
            refresh_cookie_secure=self.refresh_cookie_secure,
            refresh_cookie_samesite=self.refresh_cookie_samesite,
        )

    @cached_property
    def meta(self) -> MetaSettings:
        return MetaSettings(
            app_id=self.meta_app_id,
            app_secret=self.meta_app_secret,
            graph_version=self.meta_graph_version,
            oauth_redirect_uri=self.meta_oauth_redirect_uri,
            oauth_scopes=self.meta_oauth_scopes,
            oauth_config_id=self.meta_oauth_config_id,
            exchange_long_lived_token=self.meta_exchange_long_lived_token,
        )

    @cached_property
    def llm(self) -> LLMSettings:
        return LLMSettings(
            anthropic_api_key=self.internal_anthropic_api_key,
            anthropic_model=self.internal_anthropic_model,
            anthropic_version=self.anthropic_version,
            openai_default_model=self.openai_default_model,
            gemini_default_model=self.gemini_default_model,
            max_tokens=self.llm_max_tokens,
        )


settings = AppSettings()
