from __future__ import annotations

import asyncio
import httpx

from ..config import settings


class LLMProxyError(Exception):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _response_payload(response: httpx.Response) -> dict[str, object]:
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _extract_error_message(payload: dict[str, object], fallback: str) -> str:
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return message.strip()

    for key in ("message", "detail"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    return fallback


def _transport_error_message(provider: str, exc: httpx.HTTPError) -> str:
    return f"{provider} request failed: {exc}"


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
            try:
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
            except httpx.HTTPError as exc:
                raise LLMProxyError(_transport_error_message("Anthropic", exc)) from exc
        data = _response_payload(response)
        if response.is_error:
            raise LLMProxyError(_extract_error_message(data, response.text.strip() or "Anthropic request failed"))
        blocks = data.get("content", [])
        if isinstance(blocks, list):
            for block in blocks:
                if isinstance(block, dict) and block.get("type") == "text":
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
            try:
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
            except httpx.HTTPError as exc:
                raise LLMProxyError(_transport_error_message("OpenAI", exc)) from exc
        data = _response_payload(response)
        if response.is_error:
            raise LLMProxyError(_extract_error_message(data, response.text.strip() or "OpenAI request failed"))
        output_text = data.get("output_text")
        if output_text:
            return str(output_text).strip()
        output = data.get("output", [])
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content_list = item.get("content", [])
                if not isinstance(content_list, list):
                    continue
                for content in content_list:
                    if not isinstance(content, dict):
                        continue
                    text = content.get("text")
                    if text:
                        return str(text).strip()
        raise LLMProxyError("OpenAI response did not contain text output")


class GeminiClient:
    async def _generate_once(
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
            try:
                response = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                    params={"key": api_key},
                    json={
                        "system_instruction": {"parts": [{"text": system_prompt}]},
                        "contents": contents,
                        "generationConfig": {"maxOutputTokens": max_tokens},
                    },
                )
            except httpx.HTTPError as exc:
                raise LLMProxyError(_transport_error_message("Gemini", exc)) from exc
        data = _response_payload(response)
        if response.is_error:
            raise LLMProxyError(
                _extract_error_message(data, response.text.strip() or "Gemini request failed"),
                status_code=response.status_code,
            )
        candidates = data.get("candidates", [])
        if isinstance(candidates, list) and candidates and isinstance(candidates[0], dict):
            content = candidates[0].get("content", {})
            parts = content.get("parts", []) if isinstance(content, dict) else []
            texts = [str(part.get("text", "")).strip() for part in parts if part.get("text")]
            if texts:
                return "\n".join(texts)
        raise LLMProxyError("Gemini response did not contain text output")

    @staticmethod
    def _is_retryable_error(exc: LLMProxyError) -> bool:
        if exc.status_code in {429, 500, 503}:
            return True
        detail = str(exc).lower()
        return "high demand" in detail or "temporarily unavailable" in detail

    async def generate(
        self,
        *,
        api_key: str,
        model: str,
        system_prompt: str,
        messages: list[dict[str, str]],
        max_tokens: int,
    ) -> str:
        fallback_model = settings.llm.gemini_fallback_model
        retry_delays = (0.75, 1.5)

        try:
            return await self._generate_once(
                api_key=api_key,
                model=model,
                system_prompt=system_prompt,
                messages=messages,
                max_tokens=max_tokens,
            )
        except LLMProxyError as exc:
            if not self._is_retryable_error(exc):
                raise
            last_exc = exc

        for delay in retry_delays:
            await asyncio.sleep(delay)
            try:
                return await self._generate_once(
                    api_key=api_key,
                    model=model,
                    system_prompt=system_prompt,
                    messages=messages,
                    max_tokens=max_tokens,
                )
            except LLMProxyError as exc:
                if not self._is_retryable_error(exc):
                    raise
                last_exc = exc

        if fallback_model and fallback_model != model:
            try:
                return await self._generate_once(
                    api_key=api_key,
                    model=fallback_model,
                    system_prompt=system_prompt,
                    messages=messages,
                    max_tokens=max_tokens,
                )
            except LLMProxyError as exc:
                if not self._is_retryable_error(exc):
                    raise
                last_exc = exc

        raise last_exc
