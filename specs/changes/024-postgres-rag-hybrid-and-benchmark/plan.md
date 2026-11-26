# План реализации: 024-postgres-rag-hybrid-and-benchmark

## Шаги
1. Обновить `backend/src/medai/db/tables.py` и создать миграцию `0002_rag_hybrid_feedback_admin.py` (добавить `user_kits.tags`, `rag_chunks`, `rag_terms`, `rag_postings`, `rag_stats`, `rag_loads`, `rag_revisions`, `message_feedback`, `message_reports`, `message_audio`, `pg_trgm` индексы).
2. Реализовать `backend/src/medai/rag/chunking.py` (секционный + contextual chunking для медицинских инструкций и overlapping chunking).
3. Реализовать `backend/src/medai/rag/embeddings.py` и `hybrid.py` (синонимическое расширение, символьный n-грамм векторный энкодер + LiteLLM adapter, Reciprocal Rank Fusion $1/(60+r)$, триграммный fuzzy поиск).
4. Реализовать `backend/src/medai/rag/postgres.py` (`PostgresMedicineStore`, `PostgresBm25Index` с set-based SQL, ревизиями, export/delete/restore).
5. Обновить `backend/src/medai/rag/cli.py` / `knowledge_load.py` и `Makefile` для полного цикла `knowledge-check`, `knowledge-load`, `knowledge-export`, `knowledge-delete`, `knowledge-restore`, `knowledge-search`.
6. Исправить `backend/src/medai/rag/benchmark.py`, добавить `benchmark_llm.py` (честный trap rejection, `Accuracy`, `Faithfulness`, `Context Precision`, ablation `BM25` vs `Hybrid`), обновить тесты и выполнить проверку `make test && make lint && make bench`.
