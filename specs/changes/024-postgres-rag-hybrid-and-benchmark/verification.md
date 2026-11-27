# Верификация 024-postgres-rag-hybrid-and-benchmark

## Проверенные требования
- **REQ-001 (Contextual & Structure-aware Chunking):** `backend/src/medai/rag/chunking.py` разбивает документы на структурные секции (*Показания*, *Дозировка*, *Противопоказания*, *Взаимодействия*) с контекстным заголовком; покрыто тестом `test_chunking_medicine_and_prose`.
- **REQ-002 (Query Expansion & Dense Embeddings):** `backend/src/medai/rag/embeddings.py` и `hybrid.py` реализуют расширение синонимов, символьный n-gram эмбеддер, косинусное сходство и слияние RRF ($k=60$); покрыто `test_embeddings_rrf_expansion_and_trigram`.
- **REQ-003 (PostgreSQL RAG Storage & Inverted Index):** `backend/src/medai/rag/postgres.py` реализует транзакционную загрузку с `pg_advisory_xact_lock`, set-based BM25/Dense поиск, историю ревизий и нечеткий `pg_trgm`/триграммный поиск; покрыто `test_postgres_rag_store_sql_and_helpers` и `test_postgres_rag_store_full_lifecycle`.
- **REQ-004 (Миграция 0002):** `backend/src/medai/db/migrations/versions/0002_rag_hybrid_feedback_admin.py` проверена совместно со схемой `tables.py` (`test_db_schema.py`).
- **REQ-005 (Knowledge CLI & Makefile):** Команды `check/load/export/delete/restore/search/benchmark` в `backend/src/medai/rag/__main__.py`.
- **REQ-006 (Честный Benchmark & Eval без утечки формулировок):** `make bench` на клиническом корпусе (`package.yaml` без разговорных подгонок, лемматизированный `MEDICAL_SYNONYMS` без брендовых шорткатов) подтверждает:
  - Base (15 запросов): `BM25` — $MRR = 0.8333$, $\text{Recall@3} = 0.6000$, $\text{Recall@5} = 0.7000$, Context Precision $= 0.7872$, Accuracy $= 0.6000$, Faithfulness $= 1.0000$, Correct Rejection Rate $= 1.0000$, $P_{95} = 2.896\text{ мс}$; `HYBRID` — $MRR = 0.8833$, $\text{Recall@3} = 0.7000$, $\text{Recall@5} = 0.8000$, Accuracy $= 0.8000$, Rej $= 1.0000$.
  - Extended Ablation (30 запросов: 20 клинических + 10 ловушек): `HYBRID` ($MRR=0.9250$, $\text{Recall@3}=0.8300$, $\text{Recall@5}=0.9067$, Context Precision $=0.9117$, Accuracy $=1.0000$, Rej $=1.0000$) превосходит `BM25` ($MRR=0.8750$, $\text{Recall@3}=0.7033$, $\text{Recall@5}=0.8567$, Accuracy $=0.6500$, Rej $=0.8000$) и `DENSE` ($MRR=0.8833$, $\text{Recall@3}=0.7800$, Accuracy $=0.6000$, Rej $=1.0000$).

## Доказательство прогона команд
```text
$ make lint && make test
All checks passed!
60 passed, 1 skipped in 28.90s (unit + API)
4 passed (frontend/tests/api.test.js)

$ make bench
BASE-15 BM25: MRR=0.8333, R@3=0.6000, R@5=0.7000, Prec=0.7872, Acc=0.6000, Rej=1.0000, P95=2.896ms
EXT-30 HYBRID: MRR=0.9250, R@3=0.8300, R@5=0.9067, Prec=0.9117, Acc=1.0000, Rej=1.0000, Faith=1.0000, P95=16.33ms
```
