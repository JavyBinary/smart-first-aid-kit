# Верификация 027-ux-dialog-memory-kit-priority-and-safety

## Проверенные требования
- **REQ-001 (Профиль и RBAC):** Подтверждено живыми запросами `POST /api/v1/auth/register` -> `GET /api/v1/auth/me` -> `PATCH /api/v1/auth/me` (`200 OK`) с обновлением имени в PostgreSQL; `#adminQuickSwitchBtn` скрыт по умолчанию в [frontend/index.html](../../../frontend/index.html).
- **REQ-002 (Ротация сессий и память диалогов):** Подтвержден успешный `POST /api/v1/auth/refresh` (`200 OK`) без `500 IntegrityError`, сохранение и учет контекста из предыдущего сообщения в `Q2`.
- **REQ-003 (Приоритет аптечки и безопасность):** Подтверждено unit-тестом `test_headache_prioritizes_valid_paracetamol_in_kit_over_combo_and_ibuprofen` и живым запросом `POST /api/v1/chat/query` (`recommendation.medicine_name == "Парацетамол (500 мг)"`, `in_user_kit == True`, расчет дозировки под вес `44 кг`).
- **REQ-004 (Предзагрузка RAG, ретраи и чистый текст):** Подтверждено тестами `test_litellm_provider_retries_rate_limit`, `test_quirky_off_corpus_question_keeps_recommendation_none_with_live_llm` и живым ответом на нестандартный вопрос (`used_llm == True`, `recommendation is None`, без Markdown `**` / `###`).
- **REQ-005 (Аптека, Медкарта, редактирование, TTS и UI):** Проверены `POST /api/v1/kit/items` (`201`) -> `PUT /api/v1/kit/items/{id}` (`200`), 4 unit-теста `frontend/tests/api.test.js` (`4/4 passed`), расширенные каталоги в `Catalog.js` (46 препаратов) и `MedicalCatalogModal.js` (62 диагноза, 45 аллергенов) и 5 голосов TTS.

## Доказательство прогона команд
```text
$ make lint && make test
All checks passed!
63 passed, 1 skipped (backend tests/test_agent_and_safety.py + full suite)
4 passed, 0 failed (frontend Node tests)
```
