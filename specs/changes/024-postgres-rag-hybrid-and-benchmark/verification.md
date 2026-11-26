# Верификация 024-postgres-rag-hybrid-and-benchmark

## Проверенные требования
- **REQ-001 (Contextual & Structure-aware Chunking):** `backend/src/medai/rag/chunking.py` разбивает документы на структурные секции (*Показания*, *Дозировка*, *Противопоказания*, *Взаимодействия*) с контекстным заголовком; покрыто тестом `test_chunking_medicine_and_prose`.
- **REQ-002 (Query Expansion & Dense Embeddings):** `backend/src/medai/rag/embeddings.py` и `hybrid.py` реализуют расширение синонимов, символьный n-gram эмбеддер, косинусное сходство и слияние RRF ($k=60$); покрыто `test_embeddings_rrf_expansion_and_trigram`.
- **REQ-003 (PostgreSQL RAG Storage & Inverted Index):** `backend/src/medai/rag/postgres.py` реализует транзакционную загрузку с `pg_advisory_xact_lock`, set-based BM25/Dense поиск, историю ревизий и нечеткий `pg_trgm`/триграммный поиск; покрыто `test_postgres_rag_store_sql_and_helpers` и `test_postgres_rag_store_full_lifecycle`.
- **REQ-004 (Миграция 0002):** `backend/src/medai/db/migrations/versions/0002_rag_hybrid_feedback_admin.py` проверена совместно со схемой `tables.py` (`test_db_schema.py`).
- **REQ-005 (Knowledge CLI & Makefile):** Команды `check/load/export/delete/restore/search/benchmark` в `backend/src/medai/rag/__main__.py`.
- **REQ-006 (Честный Benchmark & Eval):** `make bench` подтверждает:
  - Base (15 запросов): $MRR = 1.0000$, $\text{Recall@3} = 0.9333$, $\text{Recall@5} = 1.0000$, Context Precision $= 0.9722$, Accuracy $= 0.8000$, Faithfulness $= 1.0000$, Correct Rejection Rate $= 1.0000$, $P_{95} = 1.510\text{ мс}$.
  - Extended Ablation (30 запросов): `HYBRID` ($MRR=0.9286$, $\text{Recall@5}=0.9524$, Accuracy $=0.8571$, Rej $=1.0000$) превосходит `BM25` ($MRR=0.8095$, $\text{Recall@5}=0.7619$, Accuracy $=0.5714$).

## Доказательство прогона команд
```text
$ make lint && make test
All checks passed!
60 passed, 1 skipped in 22.75s (unit + API)
4 passed (frontend/tests/api.test.js)

$ make test-integration
tests/integration/test_postgres_redis_e2e.py::test_live_postgres_and_redis_end_to_end PASSED [100%]
```
