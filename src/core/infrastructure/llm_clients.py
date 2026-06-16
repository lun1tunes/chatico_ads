from __future__ import annotations

import httpx

from ..config import settings


class LLMProxyError(Exception):
    pass


class AnthropicClient:
    async def generate(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int,
    ) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "content-type": "application/json",
                    "x-api-key": api_key,
                    "anthropic-version": settings.llm.anthropic_version,
                },
                json={
                    "model": model,
                    "system": system_prompt,
                    "messages": messages,
                    "max_tokens": max_tokens,
                },
            )
        data = response.json()
        if response.is_error:
            raise LLMProxyError(str(data))
        blocks = data.get("content", [])
        for block in blocks:
            if block.get("type") == "text":
                return str(block.get("text", "")).strip()
        raise LLMProxyError("Anthropic response did not contain text output")


class OpenAIClient:
    async def generate(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int,
    ) -> str:
        input_payload = [
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
        ]
        for message in messages:
            input_payload.append(
                {
                    "role": message["role"],
                    "content": [{"type": "input_text", "text": message["content"]}],
                }
            )

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "content-type": "application/json",
                    "authorization": f"Bearer {api_key}",
                },
                json={
                    "model": model,
                    "input": input_payload,
                    "max_output_tokens": max_tokens,
                },
            )
        data = response.json()
        if response.is_error:
            raise LLMProxyError(str(data))
        output_text = data.get("output_text")
        if output_text:
            return str(output_text).strip()
        for item in data.get("output", []):
            for content in item.get("content", []):
                text = content.get("text")
                if text:
                    return str(text).strip()
        raise LLMProxyError("OpenAI response did not contain text output")


class GeminiClient:
    async def generate(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int,
    ) -> str:
        contents = []
        for message in messages:
            role = "model" if message["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": message["content"]}]})

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                params={"key": api_key},
                json={
                    "system_instruction": {"parts": [{"text": system_prompt}]},
                    "contents": contents,
                    "generationConfig": {"maxOutputTokens": max_tokens},
                },
            )
        data = response.json()
        if response.is_error:
            raise LLMProxyError(str(data))
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            texts = [str(part.get("text", "")).strip() for part in parts if part.get("text")]
            if texts:
                return "\n".join(texts)
        raise LLMProxyError("Gemini response did not contain text output")
