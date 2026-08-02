from __future__ import annotations

import re

from ..config import settings
from ..infrastructure.llm_clients import LLMProxyError

_AUTO_VERDICT_LABEL_RE = re.compile(
    r"^\s*(?:[-*]\s*)?\*{0,2}(?:what works|what's working|what underperforms|what's underperforming|next action|supporting details):\*{0,2}\s*",
    re.IGNORECASE,
)


def _normalize_auto_verdict_text(*, text: str, language: str) -> str:
    normalized_language = (language or "en").strip().lower() or "en"
    cleaned_lines: list[str] = []
    for raw_line in text.strip().splitlines():
        line = _AUTO_VERDICT_LABEL_RE.sub("", raw_line).strip()
        if normalized_language != "en" and line in {"-"}:
            continue
        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned or text.strip()


class LLMProxyService:
    def __init__(self, *, anthropic_client, openai_client, gemini_client) -> None:
        self.anthropic_client = anthropic_client
        self.openai_client = openai_client
        self.gemini_client = gemini_client

    def list_supported_providers(self) -> list[dict[str, object]]:
        return [
            {
                "key": "gemini",
                "label": "Gemini",
                "default_model": settings.llm.gemini_default_model,
                "presets": [
                    {
                        "value": settings.llm.gemini_default_model,
                        "label": settings.llm.gemini_default_model,
                        "is_default": True,
                    },
                    {
                        "value": settings.llm.gemini_fallback_model,
                        "label": settings.llm.gemini_fallback_model,
                        "is_default": False,
                    },
                ],
                "supports_custom_model": True,
            },
            {
                "key": "anthropic",
                "label": "Anthropic",
                "default_model": settings.llm.anthropic_model,
                "presets": [
                    {
                        "value": settings.llm.anthropic_model,
                        "label": settings.llm.anthropic_model,
                        "is_default": True,
                    }
                ],
                "supports_custom_model": True,
            },
            {
                "key": "openai",
                "label": "OpenAI",
                "default_model": settings.llm.openai_default_model,
                "presets": [
                    {
                        "value": settings.llm.openai_default_model,
                        "label": settings.llm.openai_default_model,
                        "is_default": True,
                    }
                ],
                "supports_custom_model": True,
            },
        ]

    def normalize_provider(self, provider: str) -> str:
        normalized = provider.lower().strip()
        if normalized not in {"anthropic", "openai", "gemini"}:
            raise LLMProxyError("Unsupported AI provider")
        return normalized

    def _client_for_provider(self, provider: str):
        return {
            "anthropic": self.anthropic_client,
            "openai": self.openai_client,
            "gemini": self.gemini_client,
        }[provider]

    async def _generate_with_provider(
        self,
        *,
        provider: str,
        api_key: str,
        model: str | None,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int,
    ) -> str:
        normalized_provider = self.normalize_provider(provider)
        normalized_messages = self._normalize_messages(provider=normalized_provider, messages=messages)
        selected_model = (
            model
            or {
                "anthropic": settings.llm.anthropic_model,
                "openai": settings.llm.openai_default_model,
                "gemini": settings.llm.gemini_default_model,
            }[normalized_provider]
        )
        return await self._client_for_provider(normalized_provider).generate(
            api_key=api_key,
            model=selected_model,
            system_prompt=system_prompt,
            messages=normalized_messages,
            max_tokens=max_tokens,
        )

    def _normalize_messages(self, *, provider: str, messages: list[dict[str, str]]) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []

        for message in messages:
            role = str(message.get("role", "")).strip().lower()
            content = str(message.get("content", "")).strip()
            if role not in {"user", "assistant"} or not content:
                continue

            if normalized and normalized[-1]["role"] == role:
                normalized[-1]["content"] = f"{normalized[-1]['content']}\n\n{content}"
                continue

            normalized.append({"role": role, "content": content})

        if provider == "anthropic":
            while normalized and normalized[0]["role"] == "assistant":
                normalized.pop(0)

            if normalized and normalized[-1]["role"] != "user":
                raise LLMProxyError("The last chat message must come from the user")

        if not normalized or not any(message["role"] == "user" for message in normalized):
            raise LLMProxyError("Add at least one user message before sending the chat request")

        return normalized

    async def generate_auto_verdict(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        language: str,
        provider: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> str:
        normalized_language = (language or "ru").strip().lower() or "ru"

        if provider is not None or api_key is not None:
            response_text = await self._generate_with_provider(
                provider=provider or "gemini",
                api_key=api_key or "",
                model=model,
                system_prompt=system_prompt,
                messages=messages,
                max_tokens=min(settings.llm.max_tokens, 420),
            )
            return _normalize_auto_verdict_text(text=response_text, language=normalized_language)

        available_providers = settings.llm.internal_auto_verdict_providers
        if not available_providers:
            raise LLMProxyError("Internal AI summary is not configured")

        last_exc: LLMProxyError | None = None
        for internal_provider in available_providers:
            try:
                response_text = await self._generate_with_provider(
                    provider=internal_provider,
                    api_key=settings.llm.resolve_internal_api_key_for_provider(internal_provider),
                    model=settings.llm.resolve_internal_model_for_provider(internal_provider),
                    system_prompt=system_prompt,
                    messages=messages,
                    max_tokens=min(settings.llm.max_tokens, 420),
                )
                return _normalize_auto_verdict_text(text=response_text, language=normalized_language)
            except LLMProxyError as exc:
                last_exc = exc

        raise last_exc or LLMProxyError("Internal AI summary is not configured")

    async def chat_with_internal_credentials(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> str:
        provider = settings.llm.resolved_internal_chat_provider
        api_key = settings.llm.resolve_internal_chat_api_key()
        if not api_key or api_key.startswith("replace_with_real_"):
            raise LLMProxyError("Internal AI chat is not configured")

        return await self._generate_with_provider(
            provider=provider,
            api_key=api_key,
            model=settings.llm.resolve_internal_chat_model(),
            system_prompt=system_prompt,
            messages=messages,
            max_tokens=settings.llm.max_tokens,
        )

    async def chat(
        self,
        *,
        provider: str,
        api_key: str,
        model: str | None,
        system_prompt: str,
        messages: list[dict[str, str]],
    ) -> str:
        return await self._generate_with_provider(
            provider=provider,
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            messages=messages,
            max_tokens=settings.llm.max_tokens,
        )
