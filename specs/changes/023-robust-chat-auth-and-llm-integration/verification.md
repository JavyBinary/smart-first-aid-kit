# Верификация: 023-robust-chat-auth-and-llm-integration

## Результаты тестирования

### 1. Модульные и интеграционные тесты (`make test`)
```text
============================= test session starts ==============================
collected 48 items

tests/test_auth.py::test_argon2_password_hasher PASSED                   [  2%]
tests/test_auth.py::test_token_codec_lifecycle PASSED                    [  4%]
tests/test_auth.py::test_rate_limiter PASSED                             [  6%]
tests/test_auth.py::test_auth_service_full_flow PASSED                   [  8%]
tests/test_auth.py::test_auth_api_endpoints PASSED                       [ 10%]
tests/test_auth.py::test_admin_users_api PASSED                          [ 12%]
tests/test_auth.py::test_create_admin_cli PASSED                         [ 14%]
tests/test_benchmark.py::test_load_benchmark_dataset PASSED              [ 16%]
tests/test_benchmark.py::test_benchmark_runner_metrics_thresholds PASSED [ 18%]
tests/test_benchmark.py::test_run_benchmark_convenience PASSED           [ 20%]
tests/test_bm25.py::test_normalize_text PASSED                           [ 22%]
tests/test_bm25.py::test_simple_analyzer PASSED                          [ 25%]
tests/test_bm25.py::test_morph_analyzer_lemmatization PASSED             [ 27%]
tests/test_bm25.py::test_bm25_idf_mathematics PASSED                     [ 29%]
tests/test_bm25.py::test_bm25_term_score_and_saturation PASSED           [ 31%]
tests/test_bm25.py::test_bm25_score_computation PASSED                   [ 33%]
tests/test_bm25.py::test_bm25_ranking_ordering PASSED                    [ 35%]
tests/test_bm25.py::test_in_memory_bm25_index PASSED                     [ 37%]
tests/test_bm25.py::test_load_package_from_yaml PASSED                   [ 39%]
tests/test_bm25.py::test_knowledge_load_main PASSED                      [ 41%]
tests/test_config.py::test_load_config_defaults PASSED                   [ 43%]
tests/test_config.py::test_load_config_custom_env PASSED                 [ 45%]
tests/test_config.py::test_config_models_frozen PASSED                   [ 47%]
tests/test_config.py::test_config_models_forbid_extra PASSED             [ 50%]
tests/test_db_schema.py::test_metadata_contains_all_tables PASSED        [ 52%]
tests/test_db_schema.py::test_users_table_structure_and_constraints PASSED [ 54%]
tests/test_db_schema.py::test_user_kits_table_and_constraints PASSED     [ 56%]
tests/test_db_schema.py::test_health_profiles_table_and_constraints PASSED [ 58%]
tests/test_db_schema.py::test_dialogs_and_messages_hierarchy PASSED      [ 60%]
tests/test_db_schema.py::test_rag_tables_relationship PASSED             [ 62%]
tests/test_db_schema.py::test_create_engine_configuration PASSED         [ 64%]
tests/test_db_schema.py::test_ddl_compilation_postgresql_dialect PASSED  [ 66%]
tests/test_migration_0001_initial_schema_validity PASSED                 [ 68%]
tests/test_dialogs.py::test_make_title_formatting PASSED                 [ 70%]
tests/test_dialogs.py::test_in_memory_event_broker_lifecycle PASSED      [ 72%]
tests/test_dialogs.py::test_in_memory_history_store PASSED               [ 75%]
tests/test_dialogs.py::test_dialog_service_processing PASSED             [ 77%]
tests/test_dialogs.py::test_dialog_api_http_and_chat_query PASSED        [ 79%]
tests/test_kit_and_profile.py::test_kit_item_expiry_computation PASSED   [ 81%]
tests/test_kit_and_profile.py::test_in_memory_kit_store_crud_and_isolation PASSED [ 83%]
tests/test_kit_and_profile.py::test_in_memory_profile_store PASSED       [ 85%]
tests/test_kit_and_profile.py::test_kit_and_profile_api_endpoints PASSED [ 87%]
tests/test_observability.py::test_utc_now_format PASSED                  [ 89%]
tests/test_observability.py::test_bind_context_lifecycle PASSED          [ 91%]
tests/test_observability.py::test_bind_context_invalid_key PASSED        [ 93%]
tests/test_observability.py::test_log_event_safe_and_unsafe_fields PASSED [ 95%]
tests/test_observability.py::test_event_formatter_human_and_json PASSED  [ 97%]
tests/test_observability.py::test_request_log_middleware_and_health_endpoint PASSED [100%]

============================= 48 passed in 13.58s ==============================
```

### 2. Проверка бенчмарка BM25 (`make bench`)
```text
======================================================================
          РЕЗУЛЬТАТЫ БЕНЧМАРКА BM25 (MedAI — КТ2)
======================================================================
Документов в корпусе:      30
Всего тестовых запросов:   15 (Нормальных: 10, Ловушек: 5)
----------------------------------------------------------------------
MRR (Mean Reciprocal Rank): 1.0000  (Цель: >= 0.80)
Recall@1:                   0.3333
Recall@3:                   0.9333  (Цель: >= 0.85)
Recall@5:                   1.0000  (Цель: >= 0.92)
Correct Rejection Rate:     1.0000  (Цель: 1.0000)
Latency P95:                3.807 мс (Цель: <= 15.0 мс)
======================================================================
```

### 3. Соответствие требованиям
- **REQ-001 (Out-of-Domain Guardrail):** Реализован в `medai/dialogs/guardrails.py`. Запросы вне медицинской сферы возвращают статус `out_of_domain` и вежливый клинический отказ без падения UI.
- **REQ-002 (Kit Context Enrichment):** Запросы с прикрепленными лекарствами («что это», «как принимать») обогащаются метаданными из корпуса знаний, выдается дозировка и противопоказания.
- **REQ-003 (LLM & Assistant Synthesis):** Детерминированный клинический синтез адаптирован к текстовому и структурированному выводу без обязательного требования к наличию поля `medicine_name`.
- **REQ-004 (Admin Users API):** Эндпоинт `GET /api/v1/auth/admin/users` возвращает реальный список пользователей из PostgreSQL при наличии роли `admin`/`superadmin`.
- **REQ-005 (Frontend Resilient Chat):** В `Chat.js` добавлен безопасный рендеринг, `try ... finally` для разблокировки интерфейса и сброса статуса маскота.
- **REQ-006 (Cookie Auth & Session Restore):** `client.js` использует относительный путь `/api/v1` и `credentials: 'include'`; сессия восстанавливается через `GET /api/v1/auth/me`.
- **REQ-007 (Empty Default State):** Удален `DEFAULT_KIT` и дефолтные аллергии; новые пользователи начинают с чистой аптечкой и чистой медкартой.
- **REQ-008 (Admin Table Integration):** Таблица в `admin.html` динамически загружает зарегистрированных пользователей через `authApi.getAdminUsers()`.

### 4. Комплексная E2E верификация в Docker Compose (`http://127.0.0.1:8090`)

1. **Немедицинский запрос («как готовить блины»):**
   ```bash
   curl -s -X POST http://127.0.0.1:8090/api/v1/chat/query \
     -H "Content-Type: application/json" \
     -d '{"query":"как готовить блины"}'
   ```
   **Результат:** Статус 200 OK, `status: "out_of_domain"`, `recommendation: null`, корректный вежливый отказ без сбоя в чате.

2. **Запрос с лекарством из аптечки («что это» + «Парацетамол»):**
   ```bash
   curl -s -X POST http://127.0.0.1:8090/api/v1/chat/query \
     -H "Content-Type: application/json" \
     -d '{"query":"что это", "selected_pills":["Парацетамол"]}'
   ```
   **Результат:** Статус 200 OK, `status: "success"`, подробное описание препарата, дозировка, противопоказания и структурированная карточка.

3. **Регистрация пользователя, HttpOnly cookies и восстановление сессии:**
   ```bash
   curl -s -i -c /tmp/cookies.txt -X POST http://127.0.0.1:8090/api/v1/auth/register \
     -H "Content-Type: application/json" \
     -d '{"name":"Тестовый Юзер","email":"testuser@medai.local","password":"SecurePassword123!"}'
   curl -s -i -b /tmp/cookies.txt http://127.0.0.1:8090/api/v1/auth/me
   ```
   **Результат:** 200 OK, куки `access_token` и `refresh_token` установлены, `GET /api/v1/auth/me` возвращает профиль пользователя.

4. **Административный эндпоинт (`GET /api/v1/auth/admin/users`):**
   - Без авторизации: 401 Unauthorized (`Authentication required`).
   - С ролью superadmin: 200 OK, возвращен актуальный список пользователей из PostgreSQL.

