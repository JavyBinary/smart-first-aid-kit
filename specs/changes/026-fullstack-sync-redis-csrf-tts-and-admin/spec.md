# 026-fullstack-sync-redis-csrf-tts-and-admin: Сквозная интеграция, Redis Security, Admin 2.0 и Voice TTS

## Цель
Завершить полную интеграцию всех экранов пользовательского и административного интерфейса с PostgreSQL и Redis: подключить Redis rate-limiter и blacklist JWT-токенов, добавить защиту от CSRF (`ForbiddenOriginMiddleware`), эндпоинт смены пароля, оценки/жалобы пользователей, серверную + клиентскую озвучку инструкций, полноценную панель администратора без заглушек (статистика, жалобы, CRUD корпуса лекарств, управление ролями, живой benchmark) и интеграционный тестовый контур Docker.

## Требования
- **REQ-001 (Redis Security):** Реализовать `RedisAttemptLimiter` и `TokenBlacklist` (`RedisTokenBlacklist` + `InMemoryTokenBlacklist`), интегрировать их в `AuthService` (проверка при аутентификации, отзыв при `logout` и `change-password`).
- **REQ-002 (Auth Hardening & Password Change):** Добавить `POST /api/v1/auth/change-password`, `ForbiddenOriginMiddleware` (`Sec-Fetch-Site` защита от CSRF) и роутер смены ролей `PATCH /api/v1/auth/admin/users/{id}/role`.
- **REQ-003 (Admin Stats, Reports & Corpus CRUD API):** Создать `backend/src/medai/admin/` с реальной статистикой из PostgreSQL (`GET /api/v1/admin/stats?period=7|30|90`), модерацией жалоб (`GET/PATCH /api/v1/admin/reports`), управлением корпусом (`GET/POST/PUT/DELETE /api/v1/admin/medicines` с переиндексацией в реальном времени) и запуском бенчмарка (`GET /api/v1/admin/benchmark`).
- **REQ-004 (Speech / Voice First-Aid TTS):** Создать `backend/src/medai/speech/` (`POST/GET /api/v1/dialogs/{id}/messages/{msg_id}/audio`) с поддержкой локального синтеза (Silero TTS v5 при наличии модели) и клиентским Web Speech API fallback для озвучки инструкций и шагов первой помощи.
- **REQ-005 (Frontend Full DB Integration):**
  - Синхронизация аптечки (`kit.api.js`) без запрещенных полей (`422` fix) с редактированием и анализом просрочки/дублей.
  - Синхронизация медкарты (`/api/v1/profile`) в `Kit.js` и `store.js`.
  - Переключение чата на серверные диалоги `/api/v1/dialogs` + реальный SSE-стриминг с фоллбэком для гостей.
  - Кнопки копирования, оценок `1..5`, жалобы, озвучки ответа, выбора глубины ответа (`Кратко/Подробно`), подсказок-чипсов, таймера 15 минут при ожоге и экспорта памятки аптечки.
  - Полностью живая панель `/admin.html` без захардкоженных массивов и моков.
- **REQ-006 (Docker & Integration Test Suite):** Обновить `docker/compose.yaml` (`migrate` контейнер, Redis env), добавить `docker/compose.test.yaml`, backend-тесты новых ручек и frontend Node-тесты (`frontend/tests/`).

## Критерии приемки
- [ ] `make test` и `make lint` проходят без ошибок.
- [ ] Все пользовательские и админские сценарии работают через Caddy (`http://localhost:8090`) с сохранением в PostgreSQL и Redis.
