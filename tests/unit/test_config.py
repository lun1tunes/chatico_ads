from __future__ import annotations

import pytest

from core.config import GoogleAdsSettings, LLMSettings, MetaSettings


@pytest.mark.unit
def test_llm_settings_falls_back_to_usable_provider_when_preferred_key_is_placeholder():
    settings = LLMSettings(
        internal_ai_provider="gemini",
        internal_gemini_api_key="replace_with_server_gemini_key",
        internal_anthropic_api_key="real-anthropic-key",
    )

    assert settings.resolved_internal_provider == "anthropic"
    assert settings.resolve_internal_api_key() == "real-anthropic-key"
    assert settings.resolve_internal_model() == "claude-sonnet-4-6"
    assert settings.resolved_internal_chat_provider == "anthropic"
    assert settings.resolve_internal_chat_api_key() == "real-anthropic-key"
    assert settings.resolve_internal_chat_model() == "claude-sonnet-4-6"


@pytest.mark.unit
def test_llm_settings_returns_empty_internal_key_when_only_placeholders_are_present():
    settings = LLMSettings(
        internal_ai_provider="gemini",
        internal_gemini_api_key="replace_with_server_gemini_key",
        internal_anthropic_api_key="replace_with_server_anthropic_key",
    )

    assert settings.resolve_internal_api_key() == ""
    assert settings.resolved_internal_provider == "gemini"
    assert settings.resolve_internal_chat_api_key() == ""
    assert settings.resolved_internal_chat_provider == "gemini"


@pytest.mark.unit
def test_llm_settings_prefers_usable_gemini_key_for_internal_chat():
    settings = LLMSettings(
        internal_ai_provider="anthropic",
        internal_gemini_api_key="real-gemini-key",
        internal_anthropic_api_key="real-anthropic-key",
    )

    assert settings.resolved_internal_provider == "anthropic"
    assert settings.resolved_internal_chat_provider == "gemini"
    assert settings.resolve_internal_chat_api_key() == "real-gemini-key"
    assert settings.resolve_internal_chat_model() == "gemini-3.5-flash"


@pytest.mark.unit
def test_meta_settings_require_absolute_http_redirect_uri():
    with pytest.raises(ValueError, match="absolute http"):
        MetaSettings(
            app_id="meta-app-id",
            app_secret="meta-app-secret",
            oauth_redirect_uri="/api/v1/meta/oauth/callback",
        )


@pytest.mark.unit
def test_google_ads_settings_require_absolute_http_redirect_uri():
    with pytest.raises(ValueError, match="absolute http"):
        GoogleAdsSettings(
            developer_token="google-dev-token",
            oauth_client_id="google-client-id",
            oauth_client_secret="google-client-secret",
            oauth_redirect_uri="google-ads/callback",
        )
