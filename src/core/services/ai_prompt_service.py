from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from string import Formatter
from typing import Literal

AutoVerdictScope = Literal["account", "campaign", "ad_group", "creative"]

logger = logging.getLogger(__name__)

_PROMPT_FILE_MAP = {
    "report_content": "01_report_content.txt",
    "shared_ai_philosophy": "02_shared_ai_philosophy.txt",
    "chat_prompt": "03_chat_prompt.txt",
    "auto_verdict_prompt": "04_auto_verdict_prompt.txt",
}

_DOMAIN_REFUSAL_BY_LANGUAGE = {
    "ru": "Я могу помочь только с анализом рекламы и показателей этого рекламного кабинета.",
    "kz": "Мен тек осы жарнама кабинетіндегі жарнама мен көрсеткіштерді талдауға көмектесе аламын.",
    "en": "I can only help analyze the advertising and metrics in this ad account.",
}


class PromptTemplateError(RuntimeError):
    pass


class PromptMessageError(RuntimeError):
    pass


@dataclass(frozen=True)
class PromptBundle:
    system_prompt: str
    messages: list[dict[str, str]]
    checksums: dict[str, str]


class AIPromptService:
    def __init__(self, *, prompts_dir: str | Path | None = None) -> None:
        self.prompts_dir = Path(prompts_dir) if prompts_dir is not None else Path(__file__).resolve().parents[3] / "prompts"

    def build_chat_bundle(
        self,
        *,
        report_context: str,
        language: str,
        messages: list[dict[str, str]],
    ) -> PromptBundle:
        normalized_report_context = report_context.strip()
        prompt_texts = self._load_prompts("report_content", "shared_ai_philosophy", "chat_prompt")
        checksums = self._checksums(prompt_texts)
        if not normalized_report_context:
            logger.error("AI prompt build failed type=chat reason=empty_report_context prompt_checksums=%s", checksums)
            raise PromptTemplateError("AI prompt configuration is invalid")

        normalized_language = _normalize_language_code(language)
        shared_prompt = self._render_prompt(
            prompt_name="shared_ai_philosophy",
            template=prompt_texts["shared_ai_philosophy"],
            variables={"domain_refusal_text": _domain_refusal_text(normalized_language)},
            checksums=checksums,
        )
        chat_prompt = self._render_prompt(
            prompt_name="chat_prompt",
            template=prompt_texts["chat_prompt"],
            variables={"language": normalized_language},
            checksums=checksums,
        )
        system_prompt = f"{shared_prompt}\n\n{chat_prompt}".strip()
        try:
            messages_with_context = self._inject_chat_context(
                messages=messages,
                report_content=prompt_texts["report_content"],
                report_context=normalized_report_context,
            )
        except PromptMessageError:
            logger.error(
                "AI prompt build failed type=chat reason=no_user_message prompt_checksums=%s",
                checksums,
            )
            raise
        return PromptBundle(
            system_prompt=system_prompt,
            messages=messages_with_context,
            checksums=checksums,
        )

    def build_auto_verdict_bundle(
        self,
        *,
        report_context: str,
        language: str,
        scope: AutoVerdictScope = "account",
    ) -> PromptBundle:
        normalized_report_context = report_context.strip()
        prompt_texts = self._load_prompts("report_content", "shared_ai_philosophy", "auto_verdict_prompt")
        checksums = self._checksums(prompt_texts)
        if not normalized_report_context:
            logger.error("AI prompt build failed type=auto_verdict reason=empty_report_context prompt_checksums=%s", checksums)
            raise PromptTemplateError("AI prompt configuration is invalid")

        normalized_language = _normalize_language_code(language)
        normalized_scope = scope if scope in {"account", "campaign", "ad_group", "creative"} else "account"
        shared_prompt = self._render_prompt(
            prompt_name="shared_ai_philosophy",
            template=prompt_texts["shared_ai_philosophy"],
            variables={"domain_refusal_text": _domain_refusal_text(normalized_language)},
            checksums=checksums,
        )
        auto_verdict_prompt = self._render_prompt(
            prompt_name="auto_verdict_prompt",
            template=prompt_texts["auto_verdict_prompt"],
            variables={
                "normalized_language": normalized_language,
                "language_name": _auto_verdict_language_name(normalized_language),
                "scope_focus": _auto_verdict_scope_focus(normalized_scope),
            },
            checksums=checksums,
        )
        system_prompt = f"{shared_prompt}\n\n{auto_verdict_prompt}".strip()
        return PromptBundle(
            system_prompt=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": f"{prompt_texts['report_content']}\n\nDashboard context:\n{normalized_report_context}",
                }
            ],
            checksums=checksums,
        )

    def _inject_chat_context(
        self,
        *,
        messages: list[dict[str, str]],
        report_content: str,
        report_context: str,
    ) -> list[dict[str, str]]:
        normalized_messages = [
            {
                "role": str(message.get("role", "")),
                "content": str(message.get("content", "")),
            }
            for message in messages
        ]

        for index in range(len(normalized_messages) - 1, -1, -1):
            if normalized_messages[index]["role"].strip().lower() != "user":
                continue
            user_question = normalized_messages[index]["content"].strip()
            normalized_messages[index]["content"] = (
                f"{report_content}\n\nDashboard context:\n{report_context}\n\nUser question:\n{user_question}"
            )
            break
        else:
            raise PromptMessageError("Add at least one user message before sending the chat request")

        return normalized_messages

    def _load_prompts(self, *prompt_names: str) -> dict[str, str]:
        return {prompt_name: self._read_prompt(prompt_name) for prompt_name in prompt_names}

    def _read_prompt(self, prompt_name: str) -> str:
        filename = _PROMPT_FILE_MAP[prompt_name]
        path = self.prompts_dir / filename
        try:
            return path.read_text(encoding="utf-8").strip()
        except FileNotFoundError as exc:
            logger.error("AI prompt file is missing path=%s", path)
            raise PromptTemplateError("AI prompt configuration is invalid") from exc
        except OSError as exc:
            logger.error("AI prompt file could not be read path=%s error=%s", path, exc)
            raise PromptTemplateError("AI prompt configuration is invalid") from exc

    def _render_prompt(
        self,
        *,
        prompt_name: str,
        template: str,
        variables: dict[str, str],
        checksums: dict[str, str],
    ) -> str:
        required_variables = {
            field_name
            for _, field_name, _, _ in Formatter().parse(template)
            if field_name
        }
        missing_variables = sorted(required_variables - set(variables))
        if missing_variables:
            logger.error(
                "AI prompt variable substitution failed prompt=%s missing=%s prompt_checksums=%s",
                prompt_name,
                ",".join(missing_variables),
                checksums,
            )
            raise PromptTemplateError("AI prompt configuration is invalid")
        try:
            return template.format(**variables)
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "AI prompt rendering failed prompt=%s error=%s prompt_checksums=%s",
                prompt_name,
                exc,
                checksums,
            )
            raise PromptTemplateError("AI prompt configuration is invalid") from exc

    def _checksums(self, prompt_texts: dict[str, str]) -> dict[str, str]:
        return {
            _PROMPT_FILE_MAP[prompt_name]: hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
            for prompt_name, text in prompt_texts.items()
        }


def _normalize_language_code(language: str) -> str:
    normalized = (language or "ru").strip().lower()
    if normalized in {"ru", "kz", "en"}:
        return normalized
    return "ru"


def _domain_refusal_text(language: str) -> str:
    return _DOMAIN_REFUSAL_BY_LANGUAGE.get(language, _DOMAIN_REFUSAL_BY_LANGUAGE["ru"])


def _auto_verdict_language_name(language: str) -> str:
    if language == "ru":
        return "Russian"
    if language == "kz":
        return "Kazakh"
    return "English"


def _auto_verdict_scope_focus(scope: AutoVerdictScope) -> str:
    if scope == "campaign":
        return (
            "Focus first on the selected campaign from the dashboard context. "
            "Use account-level or ad-group details only as supporting evidence. "
            "Do not switch to an account-wide verdict."
        )
    if scope == "ad_group":
        return (
            "Focus first on the selected ad group from the dashboard context. "
            "Use campaign-level or creative-level details only to support that ad-group verdict. "
            "Do not switch to an account-wide or campaign-wide verdict."
        )
    if scope == "creative":
        return (
            "Focus first on the selected creative from the dashboard context. "
            "Compare it only with nearby peer creatives when the provided data supports that comparison. "
            "Keep the verdict centered on the selected creative."
        )
    return (
        "Focus on the overall account-level picture from the dashboard context. "
        "Use campaign, ad-group, and creative details only as supporting evidence."
    )
