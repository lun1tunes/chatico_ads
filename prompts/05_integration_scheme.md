# Chatico Ads AI Integration Scheme

## Runtime Flow

1. Dashboard services build factual `report_context` from the current ad account only.
2. `src/core/services/ai_prompt_service.py` loads prompt files from `prompts/` in UTF-8.
3. The prompt service assembles:
   - Chat: `02_shared_ai_philosophy.txt` + `03_chat_prompt.txt` as `system_prompt`, then `01_report_content.txt` + `report_context` + `user_message` inside the final user payload.
   - Auto Verdict: `02_shared_ai_philosophy.txt` + `04_auto_verdict_prompt.txt` as `system_prompt`, then `01_report_content.txt` + `report_context` inside the user payload.
4. `src/api_v1/ai/views.py` logs:
   - request type (`chat` or `auto_verdict`)
   - platform (`meta`, `google_ads`, `tiktok_ads`)
   - ad account identifier
   - report period
   - prompt file checksums
5. `src/core/services/llm_proxy_service.py` only chooses the provider, normalizes message shape, and forwards the assembled prompt bundle.

## Safety Boundaries

- The AI may discuss only the current ad account context from `report_context`.
- Shared philosophy is centralized and reused by both Chat and Auto Verdict.
- Prompt-template failures and empty `report_context` abort the request with a controlled error instead of sending a damaged prompt upstream.
- API keys and secrets are excluded from logs.

## File Ownership

- `prompts/*.txt`: editable AI behavior
- `src/core/services/ai_prompt_service.py`: prompt loading, substitution, validation, checksums
- `src/api_v1/ai/views.py`: route wiring, logging, HTTP error mapping
- `src/core/services/llm_proxy_service.py`: provider dispatch only
