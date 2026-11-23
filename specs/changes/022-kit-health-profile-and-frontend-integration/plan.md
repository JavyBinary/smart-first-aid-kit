# 022-kit-health-profile-and-frontend-integration: Инженерный план реализации

## 1. Доменные модели и интерфейсы хранилищ
1. `backend/src/medai/kit/models.py`:
   - `KitItem`, `CreateKitItemRequest`, `UpdateKitItemRequest`, `KitListResponse`.
   - Проверка срока годности `is_expired` на основе текущей даты.
2. `backend/src/medai/profile/models.py`:
   - `HealthProfile`, `UpdateHealthProfileRequest` с алиасами `chronic` / `chronic_diseases`.
3. `KitStore` и `ProfileStore` интерфейсы в `stores.py`.

## 2. Реализация PostgreSQL-хранилищ на SQLAlchemy 2.0 Core
1. `backend/src/medai/kit/postgres.py`:
   - `PostgresKitStore` для таблицы `user_kits` (`list_items`, `add_item`, `update_item`, `delete_item`).
2. `backend/src/medai/profile/postgres.py`:
   - `PostgresProfileStore` для таблицы `health_profiles` (`get_profile`, `update_profile`).
3. In-memory реализации для легковесного тестирования без внешних сервисов.

## 3. Реализация REST API роутеров
1. `backend/src/medai/kit/router.py`:
   - `GET /api/v1/kit`
   - `POST /api/v1/kit/items`
   - `PUT /api/v1/kit/items/{id}`
   - `DELETE /api/v1/kit/items/{id}`
2. `backend/src/medai/profile/router.py`:
   - `GET /api/v1/profile`
   - `PUT /api/v1/profile`

## 4. Интеграция в FastAPI приложение
1. Подключить роутеры в `backend/src/medai/main.py`.
2. Проверить CORS заголовки и обратный прокси Caddy.

## 5. Тестирование и верификация
1. Написать `backend/tests/test_kit_and_profile.py` (CRUD тесты, валидация полей, изоляция пользователей).
2. Запустить полный регресс: `make test`, `make bench`, `make lint`.
3. Сформировать `verification.md`, зафиксировать статус `done` и обновить `CHANGE_HISTORY.md`.
