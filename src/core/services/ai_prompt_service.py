from __future__ import annotations

import hashlib
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from string import Formatter
from typing import Literal

AutoVerdictScope = Literal["account", "campaign", "ad_group", "creative"]

logger = logging.getLogger(__name__)

PROMPT_FILE_MAP = {
    "report_content": "01_report_content.txt",
    "shared_ai_philosophy": "02_shared_ai_philosophy.txt",
    "chat_prompt": "03_chat_prompt.txt",
    "auto_verdict_prompt": "04_auto_verdict_prompt.txt",
}
_PROMPT_FILE_MAP = PROMPT_FILE_MAP

PROMPT_BLOCK_META = {
    "report_content": {
        "title": "Report content",
        "used_in": ("chat", "auto_verdict"),
    },
    "shared_ai_philosophy": {
        "title": "Shared AI philosophy",
        "used_in": ("chat", "auto_verdict"),
    },
    "chat_prompt": {
        "title": "Chat prompt",
        "used_in": ("chat",),
    },
    "auto_verdict_prompt": {
        "title": "Auto verdict prompt",
        "used_in": ("auto_verdict",),
    },
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


class PromptChecksumError(RuntimeError):
    pass


@dataclass(frozen=True)
class PromptBlock:
    id: str
    filename: str
    title: str
    body: str
    checksum: str
    placeholders: tuple[str, ...]
    used_in: tuple[str, ...]


@dataclass(frozen=True)
class PromptCatalog:
    revision: int
    blocks: tuple[PromptBlock, ...]


@dataclass(frozen=True)
class PromptBundle:
    system_prompt: str
    messages: list[dict[str, str]]
    checksums: dict[str, str]
    revision: int = 0
    source: str = "files"


class AIPromptService:
    def __init__(self, *, prompts_dir: str | Path | None = None) -> None:
        self.prompts_dir = Path(prompts_dir) if prompts_dir is not None else Path(__file__).resolve().parents[3] / "prompts"
        self._lock = threading.RLock()
        self._overlay: dict[str, str] = {}
        self._revision = 0
        self._defaults: dict[str, str] = {}
        for prompt_name in PROMPT_FILE_MAP:
            try:
                self._defaults[prompt_name] = self._read_file(prompt_name)
            except PromptTemplateError:
                continue

    def list_prompts(self) -> PromptCatalog:
        with self._lock:
            blocks = tuple(self._build_block(prompt_name) for prompt_name in PROMPT_FILE_MAP)
            return PromptCatalog(revision=self._revision, blocks=blocks)

    def apply_prompts(self, updates: dict[str, str]) -> PromptCatalog:
        normalized = self._normalize_prompt_map(updates)
        if not normalized:
            raise PromptTemplateError("No prompt updates provided")

        with self._lock:
            try:
                written = self._write_files(normalized)
            except PromptTemplateError:
                raise
            except OSError as exc:
                logger.error("AI prompt file could not be written error=%s", exc)
                raise PromptTemplateError("AI prompt configuration is invalid") from exc

            self._overlay.update(written)
            self._revision += 1
            logger.info(
                "AI prompts applied ids=%s revision=%s checksums=%s",
                ",".join(sorted(written)),
                self._revision,
                self._checksums(written),
            )
            return self.list_prompts()

    def reset_prompts(self, prompt_ids: list[str] | None = None) -> PromptCatalog:
        target_ids = list(PROMPT_FILE_MAP) if not prompt_ids else list(prompt_ids)
        defaults = {
            prompt_id: self._defaults[prompt_id]
            for prompt_id in target_ids
            if prompt_id in self._defaults
        }
        if not defaults:
            raise PromptTemplateError("No default prompts are available to reset")
        return self.apply_prompts(defaults)

    def build_chat_bundle(
        self,
        *,
        report_context: str,
        language: str,
        messages: list[dict[str, str]],
        prompt_overrides: dict[str, str] | None = None,
        expected_checksums: dict[str, str] | None = None,
    ) -> PromptBundle:
        normalized_report_context = report_context.strip()
        prompt_texts, source, revision = self._load_prompts(
            "report_content",
            "shared_ai_philosophy",
            "chat_prompt",
            overrides=prompt_overrides,
        )
        checksums = self._checksums(prompt_texts)
        if not normalized_report_context:
            logger.error("AI prompt build failed type=chat reason=empty_report_context prompt_checksums=%s", checksums)
            raise PromptTemplateError("AI prompt configuration is invalid")
        self._assert_expected_checksums(checksums, expected_checksums)

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
            revision=revision,
            source=source,
        )

    def build_auto_verdict_bundle(
        self,
        *,
        report_context: str,
        language: str,
        scope: AutoVerdictScope = "account",
        prompt_overrides: dict[str, str] | None = None,
        expected_checksums: dict[str, str] | None = None,
    ) -> PromptBundle:
        normalized_report_context = report_context.strip()
        prompt_texts, source, revision = self._load_prompts(
            "report_content",
            "shared_ai_philosophy",
            "auto_verdict_prompt",
            overrides=prompt_overrides,
        )
        checksums = self._checksums(prompt_texts)
        if not normalized_report_context:
            logger.error("AI prompt build failed type=auto_verdict reason=empty_report_context prompt_checksums=%s", checksums)
            raise PromptTemplateError("AI prompt configuration is invalid")
        self._assert_expected_checksums(checksums, expected_checksums)

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
            revision=revision,
            source=source,
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

    def _load_prompts(
        self,
        *prompt_names: str,
        overrides: dict[str, str] | None = None,
    ) -> tuple[dict[str, str], str, int]:
        normalized_overrides = self._normalize_prompt_map(overrides)
        texts: dict[str, str] = {}
        used_override = False
        with self._lock:
            revision = self._revision
            overlay_active = bool(self._overlay)
            for prompt_name in prompt_names:
                if prompt_name in normalized_overrides:
                    body = normalized_overrides[prompt_name].strip()
                    if not body:
                        raise PromptTemplateError("AI prompt configuration is invalid")
                    texts[prompt_name] = body
                    used_override = True
                else:
                    texts[prompt_name] = self._read_prompt(prompt_name)
        return texts, "request" if used_override else ("overlay" if overlay_active else "files"), revision

    def _read_prompt(self, prompt_name: str) -> str:
        overlay_body = self._overlay.get(prompt_name)
        if overlay_body is not None:
            return overlay_body
        return self._read_file(prompt_name)

    def _read_file(self, prompt_name: str) -> str:
        filename = PROMPT_FILE_MAP[prompt_name]
        path = self.prompts_dir / filename
        try:
            return path.read_text(encoding="utf-8").strip()
        except FileNotFoundError as exc:
            logger.error("AI prompt file is missing path=%s", path)
            raise PromptTemplateError("AI prompt configuration is invalid") from exc
        except OSError as exc:
            logger.error("AI prompt file could not be read path=%s error=%s", path, exc)
            raise PromptTemplateError("AI prompt configuration is invalid") from exc

    def _write_files(self, updates: dict[str, str]) -> dict[str, str]:
        prepared: list[tuple[str, Path, Path, str]] = []
        written: dict[str, str] = {}
        try:
            for prompt_name, body in updates.items():
                normalized_body = body.strip()
                if not normalized_body:
                    raise PromptTemplateError(f"Prompt {prompt_name} cannot be empty")
                path = self.prompts_dir / PROMPT_FILE_MAP[prompt_name]
                tmp_path = path.with_suffix(path.suffix + ".tmp")
                tmp_path.write_text(normalized_body + "\n", encoding="utf-8")
                prepared.append((prompt_name, tmp_path, path, normalized_body))
            for prompt_name, tmp_path, path, normalized_body in prepared:
                tmp_path.replace(path)
                written[prompt_name] = normalized_body
        except Exception:
            for _, tmp_path, _, _ in prepared:
                tmp_path.unlink(missing_ok=True)
            raise
        return written

    def _build_block(self, prompt_name: str) -> PromptBlock:
        body = self._read_prompt(prompt_name)
        meta = PROMPT_BLOCK_META[prompt_name]
        return PromptBlock(
            id=prompt_name,
            filename=PROMPT_FILE_MAP[prompt_name],
            title=str(meta["title"]),
            body=body,
            checksum=self._checksum_text(body),
            placeholders=tuple(self._placeholders(body)),
            used_in=tuple(meta["used_in"]),
        )

    def _normalize_prompt_map(self, values: dict[str, str] | None) -> dict[str, str]:
        if not values:
            return {}
        filename_to_id = {filename: prompt_id for prompt_id, filename in PROMPT_FILE_MAP.items()}
        normalized: dict[str, str] = {}
        for raw_key, raw_body in values.items():
            prompt_id = raw_key if raw_key in PROMPT_FILE_MAP else filename_to_id.get(raw_key)
            if prompt_id is None:
                raise PromptTemplateError(f"Unknown prompt '{raw_key}'")
            normalized[prompt_id] = str(raw_body)
        return normalized

    def _assert_expected_checksums(
        self,
        actual: dict[str, str],
        expected: dict[str, str] | None,
    ) -> None:
        if not expected:
            return
        filename_to_id = {filename: prompt_id for prompt_id, filename in PROMPT_FILE_MAP.items()}
        normalized_expected: dict[str, str] = {}
        for raw_key, checksum in expected.items():
            prompt_id = raw_key if raw_key in PROMPT_FILE_MAP else filename_to_id.get(raw_key)
            if prompt_id is None:
                raise PromptChecksumError(f"Unknown prompt checksum '{raw_key}'")
            filename = PROMPT_FILE_MAP[prompt_id]
            if filename not in actual:
                continue
            normalized_expected[filename] = str(checksum).strip().lower()
        mismatched = sorted(
            filename
            for filename, checksum in normalized_expected.items()
            if actual[filename] != checksum
        )
        if mismatched:
            logger.error(
                "AI prompt checksum mismatch files=%s expected=%s actual=%s",
                ",".join(mismatched),
                {name: normalized_expected[name] for name in mismatched},
                {name: actual[name] for name in mismatched},
            )
            raise PromptChecksumError("Applied prompt does not match the prompt used for this request")

    def _placeholders(self, template: str) -> list[str]:
        return sorted(
            {
                field_name
                for _, field_name, _, _ in Formatter().parse(template)
                if field_name
            }
        )

    def _checksum_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]

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
            PROMPT_FILE_MAP[prompt_name]: self._checksum_text(text)
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
