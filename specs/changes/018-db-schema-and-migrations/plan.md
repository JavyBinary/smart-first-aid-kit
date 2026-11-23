# 018-db-schema-and-migrations: Инженерный план реализации

## 1. Описание таблиц SQLAlchemy 2.0 Core (`backend/src/medai/db/tables.py`)
1. Создать объект `metadata = MetaData()`.
2. Описать таблицы с типами данных и ограничениями:
   - `users`: `id`, `email`, `name`, `password_hash`, `role`, `avatar_color`, `created_at`, `updated_at`. Индекс `users_email_lower_key`.
   - `refresh_sessions`: `id`, `user_id`, `family_id`, `token_hash`, `created_at`, `expires_at`, `revoked_at`, `replaced_by`.
   - `user_kits`: `id`, `user_id`, `medicine_name`, `dosage`, `form`, `category`, `status`, `expiry_date`, `quantity`, `notes`, `icon_color`, `created_at`, `updated_at`.
   - `health_profiles`: `id`, `user_id`, `age`, `weight_kg`, `chronic_diseases`, `allergies`, `special_notes`, `created_at`, `updated_at`.
   - `dialogs`: `id`, `user_id`, `title`, `created_at`, `updated_at`. Индекс `dialogs_user_id_updated_at_idx`.
   - `messages`: `id`, `dialog_id`, `position`, `role`, `content`, `rag_payload`, `created_at`. Уникальность `(dialog_id, position)`.
   - `rag_medicines`: `id`, `title`, `inn`, `atc_code`, `category`, `forms`, `indications`, `contraindications`, `dosage_text`, `interactions`, `emergency_flags`, `created_at`, `updated_at`.
   - `rag_bm25_index`: `doc_id`, `lemmatized_text`, `doc_length`, `term_frequencies`, `updated_at`.

## 2. Асинхронный движок подключения (`backend/src/medai/db/engine.py`)
1. Реализовать функцию `create_engine(config: DatabaseConfig) -> AsyncEngine`.
2. Включить `pool_pre_ping=True`, `hide_parameters=True`.

## 3. Инфраструктура миграций Alembic
1. Создать каталог `backend/src/medai/db/migrations/`:
   - `env.py`: асинхронный запуск через `run_sync` с `target_metadata = metadata`.
   - `script.py.mako`: шаблон миграций.
   - `versions/`: директория ревизий.
2. Создать модуль `backend/src/medai/db/migrate.py`:
   - Функции `upgrade()`, `downgrade()`, `main()`.
3. Создать миграцию `0001_initial_schema.py`, воспроизводящую все таблицы и индексы.

## 4. Обновление фасада `Makefile`
1. Добавить команду `make migrate` для применения миграций через `python -m medai.db.migrate`.

## 5. Тестирование и верификация
1. Написать `backend/tests/test_db_schema.py`:
   - Проверка наличия всех таблиц в `metadata.tables`.
   - Проверка колонок, типов и внешних ключей.
   - Проверка CheckConstraint на ролях, статусах, диапазонах возраста и веса.
   - Проверка генерации DDL через SQLite/PostgreSQL диалект.
2. Запустить `make test` и `make lint`.
3. Зафиксировать доказательства в `specs/changes/018-db-schema-and-migrations/verification.md`.
4. Перевести статус спецификации в `done` через `spec_status.py`.
