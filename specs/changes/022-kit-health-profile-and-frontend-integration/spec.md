# 022-kit-health-profile-and-frontend-integration: REST API аптечки, профиль здоровья и интеграция с фронтендом

## Цель
Реализовать REST API управления индивидуальной аптечкой пользователя (`/api/v1/kit`), профилем здоровья (`/api/v1/profile`), персистентность в PostgreSQL (`user_kits`, `health_profiles`), интеграцию с клиентским интерфейсом Кати и Caddy reverse-proxy контуром, завершив этап КТ2 в полном соответствии со стандартом НИРС МГТУ им. Н. Э. Баумана.

## Допущения и контекст
- Таблицы `user_kits` и `health_profiles` уже созданы миграцией `0001_initial_schema` с CheckConstraints (`status IN ('otc', 'rx')`, `quantity >= 1`, `age >= 0 AND age <= 130`, `weight_kg >= 1.0 AND weight_kg <= 300.0`).
- Все операции требуют аутентифицированного пользователя (`user_id`).
- Формат ответов полностью совместим с контрактами клиентского слоя [frontend/src/api/kit.api.js](frontend/src/api/kit.api.js) и архитектурным каталогом [docs/api.md](docs/api.md).
- В Caddyfile настроен обратный прокси `/api/*` $\rightarrow$ `backend:8000`, `/*` $\rightarrow$ `frontend:80`.

## Требования
- **REQ-001:** Создать доменные Pydantic v2 модели аптечки и профиля здоровья:
  - `KitItem`: `id`, `name`, `dosage`, `form`, `category`, `tags`, `quantity`, `expiry` (`expiry_date`), `status` (`otc`, `rx`), `is_expired`.
  - `CreateKitItemRequest`: `name`, `dosage`, `form`, `category`, `tags`, `quantity`, `expiry`, `status`.
  - `UpdateKitItemRequest`: `dosage`, `quantity`, `expiry`, `status`.
  - `HealthProfile`: `age`, `weight_kg`, `chronic_diseases`, `allergies`, `special_notes`.
  - `UpdateHealthProfileRequest`: опциональные поля для обновления.
- **REQ-002:** Реализовать `KitStore` и `PostgresKitStore` в `backend/src/medai/kit/stores.py` и `postgres.py` с контролем принадлежности `user_id`:
  - `list_items(user_id) -> list[KitItem]`
  - `add_item(user_id, item) -> KitItem`
  - `update_item(user_id, item_id, updates) -> KitItem | None`
  - `delete_item(user_id, item_id) -> bool`
- **REQ-003:** Реализовать `ProfileStore` и `PostgresProfileStore` в `backend/src/medai/profile/stores.py` и `postgres.py`:
  - `get_profile(user_id) -> HealthProfile` (создание дефолтного профиля при отсутствии)
  - `update_profile(user_id, updates) -> HealthProfile`
- **REQ-004:** Реализовать FastAPI роутер `backend/src/medai/kit/router.py`:
  - `GET /api/v1/kit` — получение списка медикаментов пользователя (`200 OK`).
  - `POST /api/v1/kit/items` — добавление препарата в аптечку (`201 Created`).
  - `PUT /api/v1/kit/items/{id}` — обновление количества или срока годности (`200 OK`).
  - `DELETE /api/v1/kit/items/{id}` — удаление препарата из аптечки (`200 OK` / `204 No Content`).
- **REQ-005:** Реализовать FastAPI роутер `backend/src/medai/profile/router.py`:
  - `GET /api/v1/profile` — получение профиля здоровья пользователя (`200 OK`).
  - `PUT /api/v1/profile` — обновление медицинской карты (`200 OK`).
- **REQ-006:** Подключить роутеры в `backend/src/medai/main.py` с lifespan-управлением и CORS.
- **REQ-007:** Изоляция пользователей: попытка редактирования или удаления чужого лекарства возвращает `404 Not Found`.

## Сценарии взаимодействия (BDD)

### Сценарий 1: Управление содержимым домашней аптечки (CRUD)
- **Given** авторизованный пользователь
- **When** пользователь отправляет `POST /api/v1/kit/items` с препаратом *"Ибупрофен 200 мг"* и сроком годности *"2027-05-01"*
- **Then** препарат сохраняется в таблице `user_kits`, метод `GET /api/v1/kit` возвращает его со статусом `is_expired=false`. При вызове `DELETE /api/v1/kit/items/{id}` препарат удаляется.

### Сценарий 2: Обновление профиля здоровья и проверка ограничений
- **Given** авторизованный пользователь
- **When** пользователь отправляет `PUT /api/v1/profile` со списком аллергий `['Пенициллины']` и хронических болезней `['Гастрит']`
- **Then** профиль успешно сохраняется в `health_profiles`, повторный `GET /api/v1/profile` возвращает обновленные данные. Попытка передать некорректный возраст (например, 200) блокируется валидатором с ошибкой `422 Unprocessable Entity`.

### Сценарий 3: Межпользовательская изоляция аптечек
- **Given** два зарегистрированных пользователя User 1 и User 2
- **When** User 2 отправляет `DELETE /api/v1/kit/items/{id_item_1}` к лекарству User 1
- **Then** сервер возвращает `404 Not Found`, запись User 1 остается нетронутой.
