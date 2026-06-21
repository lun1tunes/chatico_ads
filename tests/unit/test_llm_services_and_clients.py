from __future__ import annotations

import json

import httpx
import pytest
import respx

from core.infrastructure.llm_clients import AnthropicClient, GeminiClient, LLMProxyError, OpenAIClient
from core.services.llm_proxy_service import LLMProxyService
from core.use_cases.dashboard import GenerateAutoVerdictUseCase


class FakeLLMClient:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[dict[str, object]] = []

    async def generate(self, **kwargs):
        self.calls.append(kwargs)
        return f"{self.name}-response"


@pytest.mark.unit
@pytest.mark.service
async def test_llm_proxy_service_selects_provider_and_default_model():
    anthropic = FakeLLMClient("anthropic")
    openai = FakeLLMClient("openai")
    gemini = FakeLLMClient("gemini")
    service = LLMProxyService(
        anthropic_client=anthropic,
        openai_client=openai,
        gemini_client=gemini,
    )

    auto_text = await GenerateAutoVerdictUseCase(llm_proxy_service=service).execute(
        report_context="summary",
        language="kz",
    )
    internal_chat_text = await service.chat_with_internal_credentials(
        system_prompt="prompt",
        messages=[{"role": "user", "content": "What changed?"}],
    )
    chat_text = await service.chat(
        provider="openai",
        api_key="client-key",
        model=None,
        system_prompt="prompt",
        messages=[{"role": "user", "content": "What changed?"}],
    )

    assert auto_text == "gemini-response"
    assert internal_chat_text == "gemini-response"
    assert chat_text == "openai-response"
    assert gemini.calls[0]["api_key"] == "test-gemini-key"
    assert gemini.calls[0]["model"] == "gemini-3.5-flash"
    assert "Reply in language code 'kz'" in gemini.calls[0]["system_prompt"]
    assert "exactly two blocks separated by one blank line" in gemini.calls[0]["system_prompt"]
    assert gemini.calls[0]["max_tokens"] == 420
    assert gemini.calls[1]["api_key"] == "test-gemini-key"
    assert gemini.calls[1]["model"] == "gemini-3.5-flash"
    assert openai.calls[0]["model"] == "gpt-5-mini"
    assert service.list_supported_providers() == [
        {
            "key": "gemini",
            "label": "Gemini",
            "default_model": "gemini-3.5-flash",
            "presets": [
                {
                    "value": "gemini-3.5-flash",
                    "label": "gemini-3.5-flash",
                    "is_default": True,
                },
                {
                    "value": "gemini-3.1-flash-lite",
                    "label": "gemini-3.1-flash-lite",
                    "is_default": False,
                },
            ],
            "supports_custom_model": True,
        },
        {
            "key": "anthropic",
            "label": "Anthropic",
            "default_model": "claude-sonnet-4-6",
            "presets": [
                {
                    "value": "claude-sonnet-4-6",
                    "label": "claude-sonnet-4-6",
                    "is_default": True,
                }
            ],
            "supports_custom_model": True,
        },
        {
            "key": "openai",
            "label": "OpenAI",
            "default_model": "gpt-5-mini",
            "presets": [
                {
                    "value": "gpt-5-mini",
                    "label": "gpt-5-mini",
                    "is_default": True,
                }
            ],
            "supports_custom_model": True,
        },
    ]

    with pytest.raises(LLMProxyError, match="Unsupported AI provider"):
        await service.chat(
            provider="unknown",
            api_key="key",
            model=None,
            system_prompt="prompt",
            messages=[],
        )


@pytest.mark.unit
@pytest.mark.service
async def test_llm_proxy_service_normalizes_anthropic_chat_messages():
    anthropic = FakeLLMClient("anthropic")
    service = LLMProxyService(
        anthropic_client=anthropic,
        openai_client=FakeLLMClient("openai"),
        gemini_client=FakeLLMClient("gemini"),
    )

    text = await service.chat(
        provider="anthropic",
        api_key="client-key",
        model=None,
        system_prompt="prompt",
        messages=[
            {"role": "assistant", "content": "helper text"},
            {"role": "user", "content": "First question"},
            {"role": "assistant", "content": "Previous answer"},
            {"role": "user", "content": "Second question"},
            {"role": "noop", "content": "ignored"},
            {"role": "assistant", "content": "   "},
        ],
    )

    assert text == "anthropic-response"
    assert anthropic.calls[0]["messages"] == [
        {"role": "user", "content": "First question"},
        {"role": "assistant", "content": "Previous answer"},
        {"role": "user", "content": "Second question"},
    ]


@pytest.mark.unit
@pytest.mark.service
async def test_llm_proxy_service_rejects_prefilled_trailing_assistant_for_anthropic():
    service = LLMProxyService(
        anthropic_client=FakeLLMClient("anthropic"),
        openai_client=FakeLLMClient("openai"),
        gemini_client=FakeLLMClient("gemini"),
    )

    with pytest.raises(LLMProxyError, match="The last chat message must come from the user"):
        await service.chat(
            provider="anthropic",
            api_key="client-key",
            model=None,
            system_prompt="prompt",
            messages=[
                {"role": "user", "content": "Question"},
                {"role": "assistant", "content": "Prefill"},
            ],
        )


@pytest.mark.unit
@pytest.mark.service
@respx.mock
async def test_anthropic_client_payload_shape():
    route = respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            200,
            json={"content": [{"type": "text", "text": "anthropic ok"}]},
        )
    )

    text = await AnthropicClient().generate(
        api_key="anthropic-client-key",
        model="claude-sonnet-4-6",
        system_prompt="system prompt",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=512,
    )

    assert text == "anthropic ok"
    request_payload = json.loads(route.calls[0].request.content)
    assert request_payload["model"] == "claude-sonnet-4-6"
    assert request_payload["messages"][0]["content"] == "Hello"
    assert route.calls[0].request.headers["x-api-key"] == "anthropic-client-key"


@pytest.mark.unit
@pytest.mark.service
@respx.mock
async def test_anthropic_client_surfaces_provider_error_message():
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(
            400,
            json={"error": {"type": "invalid_request_error", "message": "assistant prefill is not supported"}},
        )
    )

    with pytest.raises(LLMProxyError, match="assistant prefill is not supported"):
        await AnthropicClient().generate(
            api_key="anthropic-client-key",
            model="claude-sonnet-4-6",
            system_prompt="system prompt",
            messages=[{"role": "assistant", "content": "Hello"}],
            max_tokens=512,
        )


@pytest.mark.unit
@pytest.mark.service
@respx.mock
async def test_openai_client_payload_shape():
    route = respx.post("https://api.openai.com/v1/responses").mock(
        return_value=httpx.Response(200, json={"output_text": "openai ok"})
    )

    text = await OpenAIClient().generate(
        api_key="openai-client-key",
        model="gpt-5-mini",
        system_prompt="system prompt",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=300,
    )

    assert text == "openai ok"
    request_payload = json.loads(route.calls[0].request.content)
    assert request_payload["model"] == "gpt-5-mini"
    assert request_payload["max_output_tokens"] == 300
    assert request_payload["input"][0]["role"] == "system"


@pytest.mark.unit
@pytest.mark.service
@respx.mock
async def test_gemini_client_payload_shape():
    route = respx.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent").mock(
        return_value=httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "gemini ok"}]}}]},
        )
    )

    text = await GeminiClient().generate(
        api_key="gemini-client-key",
        model="gemini-3.5-flash",
        system_prompt="system prompt",
        messages=[{"role": "assistant", "content": "Hello"}],
        max_tokens=400,
    )

    assert text == "gemini ok"
    request_payload = json.loads(route.calls[0].request.content)
    assert request_payload["system_instruction"]["parts"][0]["text"] == "system prompt"
    assert request_payload["generationConfig"]["maxOutputTokens"] == 400
    assert request_payload["contents"][0]["role"] == "model"


@pytest.mark.unit
@pytest.mark.service
@respx.mock
async def test_gemini_client_retries_and_falls_back_to_flash_lite(monkeypatch):
    async def _noop_sleep(_delay: float) -> None:
        return None

    monkeypatch.setattr("core.infrastructure.llm_clients.asyncio.sleep", _noop_sleep)

    primary_route = respx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent"
    ).mock(
        side_effect=[
            httpx.Response(503, json={"error": {"message": "This model is currently experiencing high demand."}}),
            httpx.Response(503, json={"error": {"message": "This model is currently experiencing high demand."}}),
            httpx.Response(503, json={"error": {"message": "This model is currently experiencing high demand."}}),
        ]
    )
    fallback_route = respx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-lite:generateContent"
    ).mock(
        return_value=httpx.Response(
            200,
            json={"candidates": [{"content": {"parts": [{"text": "gemini fallback ok"}]}}]},
        )
    )

    text = await GeminiClient().generate(
        api_key="gemini-client-key",
        model="gemini-3.5-flash",
        system_prompt="system prompt",
        messages=[{"role": "user", "content": "Hello"}],
        max_tokens=400,
    )

    assert text == "gemini fallback ok"
    assert len(primary_route.calls) == 3
    assert len(fallback_route.calls) == 1


@pytest.mark.unit
@pytest.mark.service
@respx.mock
async def test_gemini_client_surfaces_transport_error():
    respx.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent").mock(
        side_effect=httpx.ConnectError("network down")
    )

    with pytest.raises(LLMProxyError, match="Gemini request failed"):
        await GeminiClient().generate(
            api_key="gemini-client-key",
            model="gemini-3.5-flash",
            system_prompt="system prompt",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=400,
        )
