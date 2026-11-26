# MedAI — Умная домашняя аптечка

Интеллектуальный веб-сервис персональной инвентаризации домашней аптечки и безопасного подбора средств доврачебной помощи на базе **Hybrid RAG (BM25 + Dense Embeddings + RRF)** и **LLM Agent Runtime (LiteLLM)**.

Проект разрабатывается в рамках научно-исследовательской работы студентов (НИРС 2026, МГТУ им. Н. Э. Баумана, факультет ИУ, кафедра ИУ5).  
Дисциплина: *Разработка RAG-приложения с помощью LLM*.  
Преподаватель: *Кирибаев Т. Е.*  
Методические указания: *Рубинштейн И. А.*

---

## 1. Команда и роли

- **Лука (Тимлид):** Архитектура SDD, ядро BM25 + Hybrid RAG (чанкирование, `pymorphy3`, Dense + RRF, `pg_trgm`), бенчмаркинг ($MRR$, $Recall@k$, Accuracy, Faithfulness).
- **Полина:** Backend & API на FastAPI, Agent Runtime + LiteLLM, инструменты клинической безопасности, PostgreSQL/Alembic, Redis security, Admin 2.0, TTS.
- **Катя:** Дизайн-система и клиентский интерфейс КТ1 (`ui/auth.html`, `ui/site.html`, `ui/admin.html`) и модульный SPA-контур (`frontend/`).

---

## 2. Быстрый старт (Docker & Makefile)

Единой точкой входа служит [Makefile](Makefile):

```bash
# 1. Скопируйте шаблон переменных окружения (при желании укажите LLM_API_KEY от Groq/OpenRouter/OpenAI)
cp docker/.env.example docker/.env

# 2. Запустите полный контур (PostgreSQL 17, Redis 7, migrate + загрузка 30 лекарств, Backend, Frontend, Caddy)
make run

# 3. Просмотрите статусы спецификаций SDD и запустите проверки качества
make spec-list
make lint
make test
make test-integration
make bench
```

Сервис после `make run` доступен через обратный прокси Caddy на **`http://localhost:8090`**:
- **Чат, домашняя аптечка и медкарта:** `http://localhost:8090/`
- **Вход и регистрация:** `http://localhost:8090/login.html`
- **Панель администратора 2.0:** `http://localhost:8090/admin.html` (создание администратора: `make create-admin EMAIL=<email> ROLE=superadmin`)

---

## 3. Ключевые возможности системы

1. **Hybrid RAG в PostgreSQL (`backend/src/medai/rag/`):**
   - Собственная реализация **BM25** ($k_1 = 1.5$, $b = 0.75$) с русской лемматизацией `pymorphy3`.
   - Структурированное контекстное чанкирование, расширение синонимами, плотные эмбеддинги + **Reciprocal Rank Fusion (RRF)** и нечёткий поиск по триграммам `pg_trgm`.
   - CLI управления корпусом (`check`, `load`, `export`, `delete`, `restore`, `search`, `benchmark`) и версионирование ревизий в PostgreSQL (`rag_loads`, `rag_revisions`).
2. **Агент, LLM и медицинская безопасность (`backend/src/medai/agent/`):**
   - Потоковый `LiteLLMProvider` (OpenAI, Groq, OpenRouter, Ollama) + `Agent` и `ToolRegistry` (`search_medicines`, `lookup_medicine`, `get_user_safety_context`, `check_drug_interactions`).
   - Автоматический перекрёстный контроль **аллергий, хронических заболеваний (гастрит/язва), дублей действующих веществ (Парацетамол + Пенталгин) и сроков годности**.
   - Двухслойные `Guardrails`: защита от Prompt Injection, экстренные протоколы 112 (Red Flags + 15-минутный таймер при ожоге), отсечение нецелевых запросов (`out_of_domain`) и безопасный fallback при отсутствии `LLM_API_KEY`.
3. **Аутентификация, CSRF, TTS и Admin 2.0:**
   - `HttpOnly` cookie JWT (Argon2id + SHA-256 refresh rotation), `RedisRateLimiter`, `RedisTokenBlacklist` и `ForbiddenOriginMiddleware` (`Sec-Fetch-Site`).
   - Нейросетный синтез речи MP3 (`edge-tts`: 5 русских голосов `baya`, `kseniya`, `xenia`, `aidar`, `eugene`) с клиентским fallback на браузерный `SpeechSynthesis`.
   - Живая панель администратора на данных PostgreSQL: статистика `7/30/90`, оценки `1..5`, модерация жалоб, CRUD корпуса лекарств и живой Ablation-бенчмарк.

---

## 4. Структура репозитория

```text
├── Makefile                   # Единый фасад сборки, тестов, миграций, CLI и бенчмарка
├── README.md                  # Паспорт проекта и быстрый старт
├── AGENTS.md                  # Инженерный регламент и цикл SDD
├── GEMINI.md                  # Системный регламент AI-ассистентов
├── CHANGE_HISTORY.md          # Хронология релизов (Keep a Changelog)
├── backend/                   # Серверный контур (FastAPI, Agent, RAG, Postgres, Redis, TTS, Pytest)
├── data/                      # Медицинский корпус (30 препаратов) и датасеты бенчмарка (15 и 30 запросов)
├── docker/                    # compose.yaml, compose.test.yaml, Dockerfile, Caddyfile, .env.example
├── docs/                      # Архитектурный каталог, ERD, контракты API, формулы BM25/RRF и Benchmark
├── frontend/                  # Модульный SPA (index.html, login.html, admin.html, src/, tests/)
├── specs/                     # Реестр статусов (status.yaml) и пакеты спецификаций SDD (001–026)
└── ui/                        # Утвержденный интерфейс КТ1 (дизайн Каты)
```
