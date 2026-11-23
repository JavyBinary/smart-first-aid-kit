# 017-backend-infrastructure-scaffold: Инженерный план реализации

## 1. Подготовка структуры пакета `backend/`
1. Создать каталог `backend/` со следующей структурой:
   ```text
   backend/
   ├── pyproject.toml
   ├── README.md
   ├── src/
   │   └── medai/
   │       ├── __init__.py
   │       ├── config.py
   │       ├── observability.py
   │       └── main.py
   └── tests/
       ├── __init__.py
       ├── conftest.py
       ├── test_config.py
       └── test_observability.py
   ```
2. Сконфигурировать `pyproject.toml` с `hatchling`, зависимостями и профилем `ruff`.
3. Создать виртуальное окружение и зафиксировать `uv.lock` через `uv sync`.

## 2. Реализация ядра конфигурации (`backend/src/medai/config.py`)
1. Определить модели:
   - `DatabaseConfig` (строка подключения `url` к PostgreSQL).
   - `RedisConfig` (строка подключения `url` к Redis).
   - `AuthRateLimitConfig` (лимиты попыток входа и регистраций).
   - `AuthConfig` (JWT-секрет, TTL токенов, флаг безопасных cookie).
   - `LiteLLMProviderConfig` (модель, API ключ, тайм-ауты).
   - `LoggingConfig` (уровень логов, формат human/json).
   - `Config` (корневой контейнер с `extra="forbid"`, `frozen=True`).
2. Реализовать фабричную функцию `load_config(environ: Mapping[str, str] | None = None) -> Config`.

## 3. Реализация модуля наблюдаемости (`backend/src/medai/observability.py`)
1. Настроить контекстные переменные `ContextVar` для `request_id`, `dialog_id`.
2. Зафиксировать множество разрешенных полей `_SAFE_FIELDS` для предотвращения утечки PII.
3. Разработать `EventFormatter` для форматирования в текст и JSON.
4. Разработать `RequestLogMiddleware` для фиксации входящих запросов, генерации `x-request-id`, измерения времени ответа `duration_ms` и безопасного логирования завершения.

## 4. Контейнеризация и Docker (`docker/`)
1. Создать `docker/compose.yaml` с сервисами `postgres:17-alpine`, `redis:7-alpine`, `backend`, `frontend` и `caddy:2-alpine`.
2. Создать `docker/Dockerfile` для сборки Python 3.12 окружения через `uv`.
3. Создать `docker/frontend.Dockerfile` и `docker/nginx.conf` для статики.
4. Создать `docker/Caddyfile` для обратного проксирования.

## 5. Обновление фасада `Makefile`
1. Добавить фасадные цели для запуска, тестирования и линтинга `backend/` через `uv` или локальный интерпретатор.

## 6. Тестирование и верификация
1. Написать модульные тесты в `backend/tests/test_config.py` и `backend/tests/test_observability.py`.
2. Выполнить `make lint` и `make test`.
3. Зафиксировать терминальные выводы в `verification.md` и перевести спецификацию в статус `done`.
