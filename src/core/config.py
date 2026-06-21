from __future__ import annotations

from functools import cached_property
from urllib.parse import urlparse
from typing import Annotated, Self

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


def _csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _default_meta_oauth_scopes() -> list[str]:
    return ["ads_read"]


def _default_google_oauth_scopes() -> list[str]:
    return ["https://www.googleapis.com/auth/adwords"]


def _normalize_optional_secret(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _looks_like_placeholder_secret(value: str | None) -> bool:
    normalized = _normalize_optional_secret(value)
    if normalized is None:
        return True
    lowered = normalized.lower()
    return lowered.startswith("replace_with_") or lowered in {"changeme", "todo", "set_me"}


def _is_absolute_http_url(value: str) -> bool:
    parsed = urlparse(value.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


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
    oauth_scopes: list[str] = Field(default_factory=_default_meta_oauth_scopes)
    oauth_config_id: str | None = None
    exchange_long_lived_token: bool = True

    @field_validator("oauth_scopes", mode="before")
    @classmethod
    def normalize_scopes(cls, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return _csv(value)
        return _default_meta_oauth_scopes()

    @model_validator(mode="after")
    def validate_values(self) -> Self:
        if not self.app_id.strip():
            raise ValueError("META_APP_ID must be set")
        if not self.app_secret.strip():
            raise ValueError("META_APP_SECRET must be set")
        if not self.oauth_redirect_uri.strip():
            raise ValueError("META_OAUTH_REDIRECT_URI must be set")
        if not _is_absolute_http_url(self.oauth_redirect_uri):
            raise ValueError("META_OAUTH_REDIRECT_URI must be an absolute http(s) URL")
        if not self.graph_version.startswith("v"):
            self.graph_version = f"v{self.graph_version}"
        return self


class LLMSettings(BaseModel):
    internal_anthropic_api_key: str | None = None
    internal_gemini_api_key: str | None = None
    internal_ai_provider: str | None = None
    anthropic_model: str = "claude-sonnet-4-6"
    anthropic_version: str = "2023-06-01"
    openai_default_model: str = "gpt-5-mini"
    gemini_default_model: str = "gemini-3.5-flash"
    gemini_fallback_model: str = "gemini-3.1-flash-lite"
    max_tokens: int = 1200

    @field_validator("internal_anthropic_api_key", "internal_gemini_api_key", mode="before")
    @classmethod
    def normalize_optional_keys(cls, value: object) -> str | None:
        if value is None:
            return None
        return _normalize_optional_secret(str(value))

    @field_validator("internal_ai_provider", mode="before")
    @classmethod
    def normalize_internal_provider(cls, value: object) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip().lower()
        return normalized or None

    @model_validator(mode="after")
    def validate_values(self) -> Self:
        if self.internal_ai_provider and self.internal_ai_provider not in {"anthropic", "gemini"}:
            raise ValueError("INTERNAL_AI_PROVIDER must be either 'anthropic' or 'gemini'")
        if not self.internal_anthropic_api_key and not self.internal_gemini_api_key:
            raise ValueError("Set INTERNAL_GEMINI_API_KEY or INTERNAL_ANTHROPIC_API_KEY")
        self.max_tokens = max(256, int(self.max_tokens))
        return self

    def _usable_internal_api_key_for_provider(self, provider: str) -> str | None:
        if provider == "gemini":
            return (
                None if _looks_like_placeholder_secret(self.internal_gemini_api_key) else self.internal_gemini_api_key
            )
        if provider == "anthropic":
            return (
                None
                if _looks_like_placeholder_secret(self.internal_anthropic_api_key)
                else self.internal_anthropic_api_key
            )
        return None

    def _available_internal_providers(self) -> list[str]:
        providers: list[str] = []
        for provider in ("gemini", "anthropic"):
            if self._usable_internal_api_key_for_provider(provider):
                providers.append(provider)
        return providers

    @property
    def resolved_internal_provider(self) -> str:
        if self.internal_ai_provider and self._usable_internal_api_key_for_provider(self.internal_ai_provider):
            return self.internal_ai_provider
        available_providers = self._available_internal_providers()
        if available_providers:
            return available_providers[0]
        return self.internal_ai_provider or "gemini"

    def resolve_internal_api_key(self) -> str:
        return self._usable_internal_api_key_for_provider(self.resolved_internal_provider) or ""

    def resolve_internal_model(self) -> str:
        if self.resolved_internal_provider == "gemini":
            return self.gemini_default_model
        return self.anthropic_model

    @property
    def resolved_internal_chat_provider(self) -> str:
        if self._usable_internal_api_key_for_provider("gemini"):
            return "gemini"
        return self.resolved_internal_provider

    def resolve_internal_chat_api_key(self) -> str:
        return self._usable_internal_api_key_for_provider(self.resolved_internal_chat_provider) or ""

    def resolve_internal_chat_model(self) -> str:
        if self.resolved_internal_chat_provider == "gemini":
            return self.gemini_default_model
        return self.resolve_internal_model()


class GoogleAdsSettings(BaseModel):
    developer_token: str | None = None
    api_version: str = "v22"
    oauth_client_id: str | None = None
    oauth_client_secret: str | None = None
    oauth_redirect_uri: str | None = None
    oauth_scopes: list[str] = Field(default_factory=_default_google_oauth_scopes)
    oauth_access_type: str = "offline"
    oauth_include_granted_scopes: bool = True
    oauth_prompt: str | None = "consent"

    @field_validator(
        "developer_token", "oauth_client_id", "oauth_client_secret", "oauth_redirect_uri", "oauth_prompt", mode="before"
    )
    @classmethod
    def normalize_optional_strings(cls, value: object) -> str | None:
        if value is None:
            return None
        return _normalize_optional_secret(str(value))

    @field_validator("oauth_scopes", mode="before")
    @classmethod
    def normalize_scopes(cls, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return _csv(value)
        return _default_google_oauth_scopes()

    @model_validator(mode="after")
    def validate_values(self) -> Self:
        if not self.api_version.startswith("v"):
            self.api_version = f"v{self.api_version}"
        self.oauth_access_type = (self.oauth_access_type or "offline").strip().lower() or "offline"
        if self.oauth_access_type not in {"offline", "online"}:
            self.oauth_access_type = "offline"
        if self.oauth_redirect_uri and not _is_absolute_http_url(self.oauth_redirect_uri):
            raise ValueError("GOOGLE_OAUTH_REDIRECT_URI must be an absolute http(s) URL")
        return self

    @property
    def is_configured(self) -> bool:
        values = (
            self.developer_token,
            self.oauth_client_id,
            self.oauth_client_secret,
            self.oauth_redirect_uri,
        )
        return all(not _looks_like_placeholder_secret(value) for value in values)


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
    public_app_url: str = "http://localhost:8000"
    meta_report_cache_ttl_seconds: int = 45
    meta_report_snapshot_ttl_seconds: int = 2_592_000
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
    meta_oauth_scopes: Annotated[list[str], NoDecode] = Field(default_factory=_default_meta_oauth_scopes)
    meta_oauth_config_id: str | None = None
    meta_exchange_long_lived_token: bool = True
    google_ads_developer_token: str | None = Field(default=None, validation_alias="GOOGLE_ADS_DEVELOPER_TOKEN")
    google_ads_api_version: str = "v22"
    google_oauth_client_id: str | None = Field(default=None, validation_alias="GOOGLE_OAUTH_CLIENT_ID")
    google_oauth_client_secret: str | None = Field(default=None, validation_alias="GOOGLE_OAUTH_CLIENT_SECRET")
    google_oauth_redirect_uri: str | None = Field(default=None, validation_alias="GOOGLE_OAUTH_REDIRECT_URI")
    google_oauth_scopes: Annotated[list[str], NoDecode] = Field(default_factory=_default_google_oauth_scopes)
    google_oauth_access_type: str = "offline"
    google_oauth_include_granted_scopes: bool = True
    google_oauth_prompt: str | None = "consent"
    internal_anthropic_api_key: str | None = Field(default=None, validation_alias="INTERNAL_ANTHROPIC_API_KEY")
    internal_gemini_api_key: str | None = Field(default=None, validation_alias="INTERNAL_GEMINI_API_KEY")
    internal_ai_provider: str | None = Field(default=None, validation_alias="INTERNAL_AI_PROVIDER")
    internal_anthropic_model: str = "claude-sonnet-4-6"
    anthropic_version: str = "2023-06-01"
    openai_default_model: str = "gpt-5-mini"
    gemini_default_model: str = "gemini-3.5-flash"
    gemini_fallback_model: str = "gemini-3.1-flash-lite"
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
        return _default_meta_oauth_scopes()

    @field_validator("google_oauth_scopes", mode="before")
    @classmethod
    def normalize_google_scopes(cls, value: object) -> list[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return _csv(value)
        return _default_google_oauth_scopes()

    @model_validator(mode="after")
    def validate_values(self) -> Self:
        self.meta_report_cache_ttl_seconds = max(0, int(self.meta_report_cache_ttl_seconds))
        self.meta_report_snapshot_ttl_seconds = max(0, int(self.meta_report_snapshot_ttl_seconds))
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
        if not _is_absolute_http_url(self.frontend_url):
            raise ValueError("FRONTEND_URL must be an absolute http(s) URL")
        if not _is_absolute_http_url(self.public_app_url):
            raise ValueError("PUBLIC_APP_URL must be an absolute http(s) URL")
        self.internal_anthropic_api_key = _normalize_optional_secret(self.internal_anthropic_api_key)
        self.internal_gemini_api_key = _normalize_optional_secret(self.internal_gemini_api_key)
        if not self.internal_anthropic_api_key and not self.internal_gemini_api_key:
            raise ValueError("Set INTERNAL_GEMINI_API_KEY or INTERNAL_ANTHROPIC_API_KEY")
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
    def google_ads(self) -> GoogleAdsSettings:
        return GoogleAdsSettings(
            developer_token=self.google_ads_developer_token,
            api_version=self.google_ads_api_version,
            oauth_client_id=self.google_oauth_client_id,
            oauth_client_secret=self.google_oauth_client_secret,
            oauth_redirect_uri=self.google_oauth_redirect_uri,
            oauth_scopes=self.google_oauth_scopes,
            oauth_access_type=self.google_oauth_access_type,
            oauth_include_granted_scopes=self.google_oauth_include_granted_scopes,
            oauth_prompt=self.google_oauth_prompt,
        )

    @cached_property
    def llm(self) -> LLMSettings:
        return LLMSettings(
            internal_anthropic_api_key=self.internal_anthropic_api_key,
            internal_gemini_api_key=self.internal_gemini_api_key,
            internal_ai_provider=self.internal_ai_provider,
            anthropic_model=self.internal_anthropic_model,
            anthropic_version=self.anthropic_version,
            openai_default_model=self.openai_default_model,
            gemini_default_model=self.gemini_default_model,
            gemini_fallback_model=self.gemini_fallback_model,
            max_tokens=self.llm_max_tokens,
        )


settings = AppSettings()
