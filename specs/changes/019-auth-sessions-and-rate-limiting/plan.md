# 019-auth-sessions-and-rate-limiting: Инженерный план реализации

## 1. Модели и ошибки аутентификации (`backend/src/medai/auth/models.py`)
1. Определить `Role(StrEnum)`: `USER = "user"`, `ADMIN = "admin"`, `SUPERADMIN = "superadmin"`.
2. Определить Pydantic модели запросов: `RegisterRequest`, `LoginRequest`, `UserResponse`.
3. Определить доменные сущности `User`, `RefreshSession`, `AccessClaims`, `IssuedTokens`.
4. Зафиксировать иерархию исключений `AuthError`: `InvalidCredentialsError`, `LoginTakenError`, `UnauthorizedError`, `TooManyAttemptsError`.

## 2. Криптографические модули
1. `backend/src/medai/auth/passwords.py`: `Argon2PasswordHasher` с `dummy_hash` и пулом потоков.
2. `backend/src/medai/auth/tokens.py`: `TokenCodec` для HS256 JWT и SHA-256 генерации refresh токенов.

## 3. Хранилища данных и Rate Limiting
1. `backend/src/medai/auth/stores.py`: интерфейсы `UserStore`, `SessionStore`.
2. `backend/src/medai/auth/postgres.py`: `PostgresUserStore` и `PostgresSessionStore` на SQLAlchemy Core.
3. `backend/src/medai/auth/rate_limiter.py`: `RateLimiter` с поддержкой Redis и in-memory fallback для тестов.
4. `backend/src/medai/auth/service.py`: высокоуровневый `AuthService` объединяющий хешер, токены, сторы и рейт-лимитер.

## 4. Маршрутизация REST API (`backend/src/medai/auth/router.py`)
1. Реализовать роуты FastAPI:
   - `POST /register`: валидация, создание пользователя, установка cookies.
   - `POST /login`: проверка пароля, ротация сессий, установка cookies.
   - `POST /refresh`: валидация refresh токена из cookie, ротация, установка новых cookies.
   - `POST /logout`: удаление сессии в БД/Redis, сброс cookies (`max_age=0`).
   - `GET /me`: извлечение пользователя из `request.state` через FastAPI Dependency (`get_current_user`).
2. Зарегистрировать роутер в `medai.main.create_app`.

## 5. Консольная утилита `create_admin` и `Makefile`
1. Реализовать `backend/src/medai/create_admin.py` с интерактивным вводом пароля через `getpass`.
2. Добавить цель `make create-admin EMAIL=<email> [ROLE=admin|superadmin]` в `Makefile`.

## 6. Тестирование и верификация
1. Написать модульные тесты в `backend/tests/test_auth.py`:
   - Тестирование Argon2id хеширования и защиты от тайминг-атак.
   - Тестирование выпуска и декодирования JWT Access токенов.
   - Тестирование ротации refresh-токенов и отзыва семейства.
   - Тестирование REST эндпоинтов авторизации и работы с cookie.
   - Тестирование CLI `create_admin`.
2. Выполнить `make test` и `make lint`.
3. Зафиксировать доказательства в `verification.md` и перевести спецификацию в статус `done`.
