# 024-postgres-rag-hybrid-and-benchmark: PostgreSQL RAG, Hybrid Search (BM25 + RRF), Chunking и честный Benchmark

## Цель
Перенести хранение медицинского корпуса и поискового индекса BM25 в PostgreSQL (`rag_medicines`, `rag_bm25_index`, `rag_chunks`, `rag_terms`, `rag_postings`, `rag_revisions`, `rag_loads`), добавить structure-aware / contextual чанкование, гибридный поиск (BM25 + Dense Vector Embeddings + Reciprocal Rank Fusion + Query Expansion + `pg_trgm` fuzzy подсказки), CLI-управление знаниями (check/load/export/delete/restore) и исправить систему оценки качества (честная проверка вопросов-ловушек, LLM Accuracy, Faithfulness, Context Precision и сравнение BM25 vs Hybrid).

## Требования
- **REQ-001 (Contextual & Structure-aware Chunking):** Создать `backend/src/medai/rag/chunking.py` с разбиением инструкций препаратов на осмысленные секционные чанки (*Показания*, *Дозировка*, *Противопоказания*, *Взаимодействия*) с контекстным заголовком (Название, МНН, АТХ, категория) и sentence-aligned чанкингом с перекрытием для произвольных текстов.
- **REQ-002 (Query Expansion & Dense Embeddings):** Создать `backend/src/medai/rag/embeddings.py` и `hybrid.py` с расширением бытовых медицинских синонимов, интерфейсом `EmbeddingProvider` (поддержка LiteLLM embeddings + детерминированный локальный векторный энкодер на символьных n-граммах для работы без внешнего API) и объединением BM25 + Dense через **Reciprocal Rank Fusion ($k=60$)**.
- **REQ-003 (PostgreSQL RAG Storage & Inverted Index):** Создать `backend/src/medai/rag/postgres.py` (`PostgresMedicineStore` и `PostgresBm25Index`):
  - Атомарная загрузка под `pg_advisory_xact_lock`, хранение документов, чанков, термов (`df`), postings (`tf`) и статистики корпуса.
  - Set-based SQL-поиск BM25 и гибридного ранжирования непосредственно в PostgreSQL.
  - История загрузок и ревизий (`rag_loads`, `rag_revisions`), `export`, `delete`, `restore`, а также нечеткий поиск имен/МНН при опечатках (`pg_trgm` в PostgreSQL, триграммное сходство в InMemory).
- **REQ-004 (Миграция схемы 0002):** Создать `0002_rag_hybrid_feedback_admin.py` (расширение `user_kits.tags`, таблицы `rag_chunks`, `rag_terms`, `rag_postings`, `rag_stats`, `rag_loads`, `rag_revisions`, `message_feedback`, `message_reports`, `message_audio`, а также расширение `pg_trgm` и триграммные индексы в PostgreSQL).
- **REQ-005 (Knowledge CLI & Makefile):** Расширить `medai.rag` CLI подкомандами `check`, `load`, `export`, `delete`, `restore`, `search`, `benchmark`, обновив цели `Makefile`.
- **REQ-006 (Честный Benchmark & Eval):**
  - Исправить баг проверки trap-вопросов в `backend/src/medai/rag/benchmark.py`: решение об отказе принимается **только** по фактическому порогу скора / ответу системы (`answer`), без проверки `q.reference_answer`.
  - Добавить расчет `Accuracy` (наличие `required_facts`), `Context Precision`, `Faithfulness` (grounding утверждений на найденных чанках), сравнение режимов `BM25` vs `Dense` vs `Hybrid (RRF)` и адаптер `benchmark_llm.py` для живой LLM.
  - Расширить набор запросов `data/benchmark_queries.yaml` вопросами на совместимость, аббревиатуры и конфликты, сохранив совместимость с КТ2.

## Критерии приемки
- [ ] `make knowledge-load` загружает пакет `data/medicines/package.yaml` в PostgreSQL и/или валидирует целостность.
- [ ] `make bench` выводит сравнительную таблицу `BM25` vs `Hybrid (RRF)`, честный `Correct Rejection Rate` и `Accuracy`.
- [ ] Все unit-тесты (`make test`) и линтер (`make lint`) пройдены без ошибок.
