# 025-agent-runtime-litellm-and-safety: Agent Runtime, LiteLLM Streaming, Medical Tools и Guardrails

## Цель
Реализовать полноценный агентный конвейер для MedAI: асинхронный streaming провайдер `LiteLLMProvider`, цикл агента `Agent` с `ToolRegistry`, медицинские инструменты (`search_medicines`, `lookup_medicine`, `get_user_safety_context`, `check_drug_interactions`), версионированный системный промпт `prompts/system.md`, двухконтурные `Input/Output Guardrails` (Prompt Injection + Red Flags + Grounding) и детерминированный Safety-aware Fallback при отсутствии `LLM_API_KEY`.

## Требования
- **REQ-001 (Domain Models & Providers):** Создать `backend/src/medai/agent/models.py`, `errors.py`, `providers/base.py`, `providers/litellm.py` с асинхронным потоковым стримингом `litellm.acompletion(..., stream=True)`, сбором `usage` и TTFT, поддержкой reasoning моделей и безопасным логированием без утечки секретов или ПДн.
- **REQ-002 (Tool Registry & Agent Runtime):** Создать `backend/src/medai/agent/tools.py` и `runtime.py` с классом `Agent` (лимит итераций, валидация аргументов инструментов через Pydantic JSON Schema, последовательное выполнение tool calls).
- **REQ-003 (Medical & Safety Tools):** Создать `backend/src/medai/agent/medical_tools.py`:
  - `search_medicines`: гибридный поиск (BM25 + Dense + RRF) с режимами.
  - `lookup_medicine`: точный поиск препарата + нечёткий `pg_trgm`/trigram fallback при опечатках.
  - `get_user_safety_context`: загрузка реальной аптечки (включая пометки о просрочке) и медкарты пользователя (возраст, вес, аллергии, хронические болезни).
  - `check_drug_interactions`: проверка конфликтов с аллергенами, хроническими диагнозами (например, НПВП при гастрите/язве), дублирования действующих веществ (Парацетамол + Терафлю) и лекарственных взаимодействий.
- **REQ-004 (Versioned System Prompt):** Разместить системный промпт в `backend/src/medai/agent/prompts/system.md` (загрузка через `importlib.resources`), требующий цитировать источники `[Dxx]`, учитывать аллергии/просрочку и игнорировать инструкции из пользовательского ввода.
- **REQ-005 (Two-Layer Guardrails):** Расширить `backend/src/medai/dialogs/guardrails.py`: детекция Prompt Injection, Red Flags Triage (`112/103`), Off-topic отсечение и Output Grounding (`verify_output_grounding`).
- **REQ-006 (Integration with DialogService):** Подключить `Agent` в `DialogService` (и SSE-стриминг, и `/chat/query` с персонализированным контекстом аптечки и медкарты) с безопасным интеллектуальным fallback-синтезатором при отсутствии `LLM_API_KEY`.

## Критерии приемки
- [x] Стриминговый ответ `Agent.run` работает и с `FakeLLMProvider`, и с `LiteLLMProvider`.
- [x] `check_drug_interactions` детектирует дублирование действующего вещества (Парацетамол + Терафлю) и конфликты с аллергиями/гастритом.
- [x] Prompt injection атаки блокируются на входе `detect_prompt_injection`.
- [x] Все тесты (`make test`) и линтер (`make lint`) пройдены.
