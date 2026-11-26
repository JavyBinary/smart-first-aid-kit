# План реализации: 026-fullstack-sync-redis-csrf-tts-and-admin

## Шаги
1. Создать `backend/src/medai/cache/` (`blacklist.py`, `rate_limiter.py`, `__init__.py`) и интегрировать в `AuthService` + `POST /api/v1/auth/change-password`.
2. Создать `backend/src/medai/admin/` (`models.py`, `stores.py`, `router.py`) + `backend/src/medai/speech/` + `ForbiddenOriginMiddleware`, подключить всё в `main.py` с автоинициализацией корпуса в PostgreSQL / YAML и `LiteLLMProvider`.
3. Полностью синхронизировать `frontend/` (`client.js`, `auth.api.js`, `kit.api.js`, `profile.api.js`, `dialogs.api.js`, `admin.api.js`, `Chat.js`, `Kit.js`, `AccountProfileModal.js`, `app.js`, `admin.html`) с серверным API.
4. Обновить `docker/compose.yaml` (`migrate` сервис) и добавить `docker/compose.test.yaml` + автотесты backend & frontend.
5. Запустить полный контур в Docker Compose и выполнить сквозную E2E верификацию.
