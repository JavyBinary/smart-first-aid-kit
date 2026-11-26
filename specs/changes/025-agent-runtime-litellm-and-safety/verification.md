# Верификация 025-agent-runtime-litellm-and-safety

## Проверенные требования
- **REQ-001 (LiteLLMProvider & Streaming):** `backend/src/medai/agent/providers/litellm.py` и `FakeLLMProvider` (`base.py`) проверены тестами `test_litellm_provider_config_and_error_isolation` и `test_agent_tool_calling_loop_and_dialog_streaming`.
- **REQ-002 (Tool Registry & Agent Runtime):** `backend/src/medai/agent/tools.py` и `runtime.py` выполняют многошаговый вызов инструментов с ограничением итераций и строгой Pydantic-валидацией.
- **REQ-003 (Medical Safety Tools):** `backend/src/medai/agent/medical_tools.py` реализует `search_medicines`, `lookup_medicine`, `get_user_safety_context`, `check_drug_interactions` (аллергии, гастрит/язва, дубли МНН Парацетамол + Терафлю, просроченные препараты); проверено в `test_safety_cross_check_allergy_chronic_duplicates_expiry`.
- **REQ-004 (Versioned System Prompt):** `backend/src/medai/agent/prompts/system.md` загружается через `importlib.resources`.
- **REQ-005 (Two-Layer Guardrails):** `detect_prompt_injection`, `detect_emergency`, `detect_out_of_domain` и `verify_output_grounding` проверены в `test_guardrails_injection_and_grounding`.
- **REQ-006 (DialogService Integration):** Интегрировано в `dialogs/service.py` (SSE + `/chat/query`) с детерминированным безопасным fallback при отсутствии `LLM_API_KEY`.

## Доказательство прогона команд
```text
$ make lint && make test
All checks passed!
tests/test_agent_and_safety.py — 4 passed
```
