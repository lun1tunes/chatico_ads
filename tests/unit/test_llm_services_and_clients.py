from __future__ import annotations

import json

import httpx
import pytest
import respx

from core.infrastructure.llm_clients import AnthropicClient, GeminiClient, LLMProxyError, OpenAIClient
from core.services.llm_proxy_service import LLMProxyService
from core.use_cases.dashboard import AskDashboardUseCase, GenerateAutoVerdictUseCase


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
    chat_text = await AskDashboardUseCase(llm_proxy_service=service).execute(
        provider="openai",
        api_key="client-key",
        model=None,
        system_prompt="prompt",
        messages=[{"role": "user", "content": "What changed?"}],
    )

    assert auto_text == "anthropic-response"
    assert chat_text == "openai-response"
    assert anthropic.calls[0]["api_key"] == "test-anthropic-key"
    assert "Reply in language code 'kz'" in anthropic.calls[0]["system_prompt"]
    assert openai.calls[0]["model"] == "gpt-5-mini"

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
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": "gemini ok"}]
                        }
                    }
                ]
            },
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
