# План реализации: 025-agent-runtime-litellm-and-safety

## Шаги
1. Создать пакет `backend/src/medai/agent/` (`models.py`, `errors.py`, `tools.py`, `prompts/system.md`, `providers/base.py`, `providers/litellm.py`, `runtime.py`).
2. Реализовать медицинские инструменты и детектор лекарственных/аллергических конфликтов в `backend/src/medai/agent/medical_tools.py`.
3. Расширить `backend/src/medai/dialogs/guardrails.py` (Prompt Injection detector, улучшенный Out-of-domain, Red Flags, Output Grounding check).
4. Интегрировать `Agent` + `SafetyContext` (аптечка, медкарта, выбранные таблетки) в `DialogService`, `/api/v1/dialogs/{id}/messages` и `/api/v1/chat/query`.
5. Написать unit-тесты `backend/tests/test_agent_and_safety.py` и верифицировать `make test && make lint`.
