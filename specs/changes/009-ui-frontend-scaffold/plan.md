# План реализации: 009-ui-frontend-scaffold

## Основание
Реализация спецификации `specs/changes/009-ui-frontend-scaffold/spec.md`.

## Порядок выполнения
1. Создать структуру каталогов `frontend/src/{api,components,state,styles}`.
2. Создать манифест `package.json` и конфигурацию `vite.config.js`.
3. Описать дизайн-токены Сбер Еаптеки в `frontend/src/styles/tokens.css`.
4. Реализовать `client.js` и сервисные API-адаптеры `auth.api.js`, `kit.api.js`, `chat.api.js`.
5. Реализовать реактивный Store `frontend/src/state/store.js`.
6. Дополнить `Makefile` целями `run-ui` и `dev-frontend`.
