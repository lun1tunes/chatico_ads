from __future__ import annotations

from ..config import settings
from ..infrastructure.llm_clients import LLMProxyError


class LLMProxyService:
    def __init__(self, *, anthropic_client, openai_client, gemini_client) -> None:
        self.anthropic_client = anthropic_client
        self.openai_client = openai_client
        self.gemini_client = gemini_client

    async def generate_auto_verdict(self, *, report_context: str, language: str) -> str:
        prompt = (
            f"You are a paid social analyst. Reply in language code '{language}'. "
            "Be concise. State what works, what underperforms, and exactly one highest-leverage next action."
        )
        return await self.anthropic_client.generate(
            api_key=settings.llm.anthropic_api_key,
            model=settings.llm.anthropic_model,
            system_prompt=prompt + "\n\nDashboard context:\n" + report_context,
            messages=[{"role": "user", "content": "Give the automatic verdict for this advertising account."}],
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
        normalized = provider.lower().strip()
        client = {
            "anthropic": self.anthropic_client,
            "openai": self.openai_client,
            "gemini": self.gemini_client,
        }.get(normalized)
        if client is None:
            raise LLMProxyError("Unsupported AI provider")

        selected_model = model or {
            "anthropic": settings.llm.anthropic_model,
            "openai": settings.llm.openai_default_model,
            "gemini": settings.llm.gemini_default_model,
        }[normalized]

        return await client.generate(
            api_key=api_key,
            model=selected_model,
            system_prompt=system_prompt,
            messages=messages,
            max_tokens=settings.llm.max_tokens,
        )
