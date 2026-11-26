# MedAI Backend Service

Серверный сервис интеллектуальной аптечки первой помощи **MedAI** (НИРС ИУ5 МГТУ им. Н. Э. Баумана).

## Архитектура
- **Фреймворк:** FastAPI (Python 3.12, Uvicorn + SSE).
- **СУБД:** PostgreSQL 17 + `pg_trgm` (SQLAlchemy 2.0 async Core + Alembic миграции `0001`, `0002`).
- **Кэш и безопасность:** Redis 7 (`RedisRateLimiter`, `RedisTokenBlacklist`), CSRF `ForbiddenOriginMiddleware`, Argon2id + Refresh Token Rotation.
- **Поисковое ядро RAG:** собственный **BM25** (`pymorphy3`), контекстное чанкирование, **Hybrid Search (BM25 + Dense + RRF)**, таблица ревизий в PostgreSQL и Ablation Benchmark (`medai.rag`).
- **Агент и LLM:** потоковый `LiteLLMProvider`, цикл `Agent` + `ToolRegistry` (`search_medicines`, `lookup_medicine`, `get_user_safety_context`, `check_drug_interactions`) и двухслойные `Guardrails`.
- **Озвучка (TTS):** нейросетный синтез MP3 через `edge-tts` (`baya`, `kseniya`, `xenia`, `aidar`, `eugene`) на `/api/v1/speech/synthesize` и `/api/v1/dialogs/{id}/messages/{msg_id}/audio`.
- **Наблюдаемость:** структурированное JSON/human логирование с контекстом (`request_id`, `dialog_id`, `call_id`) и фильтром от утечек ПДн.

## Запуск и проверка в локальном окружении
```bash
cd backend
uv sync
PYTHONPATH=src uv run pytest -v
uv run ruff check .
```

Интеграционный прогон против живых PostgreSQL 17 и Redis 7 (из корня репозитория):
```bash
make test-integration
```
