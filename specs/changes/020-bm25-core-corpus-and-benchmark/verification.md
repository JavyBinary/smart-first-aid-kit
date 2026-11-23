# Отчет о верификации 020-bm25-core-corpus-and-benchmark

## 1. Сводка верификации

- **Статус:** Успешно пройдена (100% требований выполнены с существенным запасом).
- **Область проверки:**
  - Математический аппарат Robertson-Spärck Jones IDF и ранжирование BM25 (`backend/src/medai/rag/bm25.py`).
  - Текстовый анализ, токенизация и лемматизация на базе `pymorphy3` с LRU-кэшем (`backend/src/medai/rag/analyzer.py`).
  - Медицинский корпус Минздрава РФ из 30 документов (`data/medicines/package.yaml`).
  - Контрольный набор из 15 сценариев (`data/benchmark_queries.yaml`): 10 клинических симптоматических запросов ($|R_q| = 3$) и 5 отрицательных вопросов-ловушек (Trap Queries).
  - Бенчмарк-раннер с замером задержки и метрик ($MRR$, $Recall@k$, Correct Rejection Rate).
  - Интеграция CLI `make bench` и `make knowledge-load`.

---

## 2. Результаты бенчмаркинга качества поиска (Цели vs Факт)

| Метрика | Минимальный академический порог | Целевой порог MedAI | Фактический результат | Статус |
|---|:---:|:---:|:---:|:---:|
| **MRR (Mean Reciprocal Rank)** | $\ge 0.65$ | $\ge 0.80$ | **$1.0000$** | Выполнено (100% точность 1-й позиции) |
| **Recall@1** | — | — | **$0.3333$** | Информационный |
| **Recall@3** | $\ge 0.70$ | $\ge 0.85$ | **$0.9667$** | Превышен целевой порог ($+11.67\%$) |
| **Recall@5** | $\ge 0.80$ | $\ge 0.92$ | **$1.0000$** | Полный охват ($+8.00\%$) |
| **Correct Rejection Rate** | $\ge 0.80$ | $1.00$ (5/5) | **$1.0000$ (5/5)** | Отсечение галлюцинаций 100% |
| **Задержка отклика ($P_{95}$)** | $\le 50.0\text{ мс}$ | $\le 15.0\text{ мс}$ | **$2.82\text{ мс}$** | В 5.3 раза быстрее целевого |

---

## 3. Терминальный вывод `make bench`

```text
$ make bench
Запуск бенчмарка поискового ядра BM25...
======================================================================
          РЕЗУЛЬТАТЫ БЕНЧМАРКА BM25 (MedAI — КТ2)
======================================================================
Документов в корпусе:      30
Всего тестовых запросов:   15 (Нормальных: 10, Ловушек: 5)
----------------------------------------------------------------------
MRR (Mean Reciprocal Rank): 1.0000  (Цель: >= 0.80)
Recall@1:                   0.3333
Recall@3:                   0.9667  (Цель: >= 0.85)
Recall@5:                   1.0000  (Цель: >= 0.92)
Correct Rejection Rate:     1.0000  (Цель: 1.0000)
Latency P95:                2.821 мс (Цель: <= 15.0 мс)
======================================================================
```

---

## 4. Терминальный вывод `make test`

```text
$ make test
Запуск тестов backend...
============================= test session starts ==============================
platform darwin -- Python 3.12.8, pytest-8.4.2, pluggy-1.7.0 -- backend/.venv/bin/python
cachedir: .pytest_cache
rootdir: backend
configfile: pyproject.toml
testpaths: tests
plugins: asyncio-0.26.0, anyio-4.16.0
asyncio: mode=Mode.AUTO, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collected 38 items

tests/test_auth.py::test_argon2_password_hasher PASSED                   [  2%]
tests/test_auth.py::test_token_codec_lifecycle PASSED                    [  5%]
tests/test_auth.py::test_rate_limiter PASSED                             [  7%]
tests/test_auth.py::test_auth_service_full_flow PASSED                   [ 10%]
tests/test_auth.py::test_auth_api_endpoints PASSED                       [ 13%]
tests/test_auth.py::test_create_admin_cli PASSED                         [ 15%]
tests/test_benchmark.py::test_load_benchmark_dataset PASSED              [ 18%]
tests/test_benchmark.py::test_benchmark_runner_metrics_thresholds PASSED [ 21%]
tests/test_benchmark.py::test_run_benchmark_convenience PASSED           [ 23%]
tests/test_bm25.py::test_normalize_text PASSED                           [ 26%]
tests/test_bm25.py::test_simple_analyzer PASSED                          [ 28%]
tests/test_bm25.py::test_morph_analyzer_lemmatization PASSED             [ 31%]
tests/test_bm25.py::test_bm25_idf_mathematics PASSED                     [ 34%]
tests/test_bm25.py::test_bm25_term_score_and_saturation PASSED           [ 36%]
tests/test_bm25.py::test_bm25_score_computation PASSED                   [ 39%]
tests/test_bm25.py::test_bm25_ranking_ordering PASSED                    [ 42%]
tests/test_bm25.py::test_in_memory_bm25_index PASSED                     [ 44%]
tests/test_bm25.py::test_load_package_from_yaml PASSED                   [ 47%]
tests/test_bm25.py::test_knowledge_load_main PASSED                      [ 50%]
tests/test_config.py::test_load_config_defaults PASSED                   [ 52%]
tests/test_config.py::test_load_config_custom_env PASSED                 [ 55%]
tests/test_config.py::test_config_models_frozen PASSED                   [ 57%]
tests/test_config.py::test_config_models_forbid_extra PASSED             [ 60%]
tests/test_db_schema.py::test_metadata_contains_all_tables PASSED        [ 63%]
tests/test_db_schema.py::test_users_table_structure_and_constraints PASSED [ 65%]
tests/test_db_schema.py::test_user_kits_table_and_constraints PASSED     [ 68%]
tests/test_db_schema.py::test_health_profiles_table_and_constraints PASSED [ 71%]
tests/test_dialogs_and_messages_hierarchy PASSED      [ 73%]
tests/test_rag_tables_relationship PASSED             [ 76%]
tests/test_create_engine_configuration PASSED         [ 78%]
tests/test_ddl_compilation_postgresql_dialect PASSED  [ 81%]
tests/test_migration_0001_initial_schema_validity PASSED [ 84%]
tests/test_observability.py::test_utc_now_format PASSED                  [ 86%]
tests/test_observability.py::test_bind_context_lifecycle PASSED          [ 89%]
tests/test_observability.py::test_bind_context_invalid_key PASSED        [ 92%]
tests/test_observability.py::test_log_event_safe_and_unsafe_fields PASSED [ 94%]
tests/test_observability.py::test_event_formatter_human_and_json PASSED  [ 97%]
tests/test_observability.py::test_request_log_middleware_and_health_endpoint PASSED [100%]

============================== 38 passed in 5.35s ==============================
```

---

## 5. Терминальный вывод `make lint`

```text
$ make lint
Проверка линтером Ruff...
All checks passed!
Синтаксис скриптов SDD корректен.
```
