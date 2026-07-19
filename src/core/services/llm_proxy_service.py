from __future__ import annotations

from ..config import settings
from ..infrastructure.llm_clients import LLMProxyError


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
        report_context: str,
        language: str,
        provider: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
    ) -> str:
        normalized_language = (language or "ru").strip().lower() or "ru"
        prompt = (
            f"You are a paid social analyst. Reply in language code '{normalized_language}'. "
            "Use only the provided dashboard context. Return concise Markdown with exactly two blocks separated by one blank line. "
            "Block 1: one short paragraph of 3-4 sentences, no heading, covering what works, what underperforms, and exactly one highest-leverage next action. "
            "Block 2: 2-4 short bullet points with the most important supporting details. "
            "Keep the whole answer under 120 words. No intro, no recap, no tables, no filler."
        )
        system_prompt = prompt + "\n\nDashboard context:\n" + report_context
        messages = [{"role": "user", "content": "Give the automatic verdict for this advertising account."}]

        if provider is not None or api_key is not None:
            return await self.chat(
                provider=provider or "gemini",
                api_key=api_key or "",
                model=model,
                system_prompt=system_prompt,
                messages=messages,
            )

        available_providers = settings.llm.internal_auto_verdict_providers
        if not available_providers:
            raise LLMProxyError("Internal AI summary is not configured")

        last_exc: LLMProxyError | None = None
        for internal_provider in available_providers:
            try:
                return await self._client_for_provider(internal_provider).generate(
                    api_key=settings.llm.resolve_internal_api_key_for_provider(internal_provider),
                    model=settings.llm.resolve_internal_model_for_provider(internal_provider),
                    system_prompt=system_prompt,
                    messages=messages,
                    max_tokens=min(settings.llm.max_tokens, 420),
                )
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

        normalized_messages = self._normalize_messages(provider=provider, messages=messages)
        return await self._client_for_provider(provider).generate(
            api_key=api_key,
            model=settings.llm.resolve_internal_chat_model(),
            system_prompt=system_prompt,
            messages=normalized_messages,
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
        normalized = self.normalize_provider(provider)
        client = self._client_for_provider(normalized)

        selected_model = (
            model
            or {
                "anthropic": settings.llm.anthropic_model,
                "openai": settings.llm.openai_default_model,
                "gemini": settings.llm.gemini_default_model,
            }[normalized]
        )
        normalized_messages = self._normalize_messages(provider=normalized, messages=messages)

        return await client.generate(
            api_key=api_key,
            model=selected_model,
            system_prompt=system_prompt,
            messages=normalized_messages,
            max_tokens=settings.llm.max_tokens,
        )
