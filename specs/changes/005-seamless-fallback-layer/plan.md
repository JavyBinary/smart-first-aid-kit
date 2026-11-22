# План реализации: 005-seamless-fallback-layer

## Основание
Реализация спецификации `specs/changes/005-seamless-fallback-layer/spec.md`.

## Порядок выполнения
1. Определить единую константу `const API_BASE = 'http://localhost:8000/api/v1'` во всех HTML-файлах.
2. Реализовать асинхронные обработчики `auth/login`, `auth/register`, `kit`, `chat/query`, `admin/corpus`.
3. Добавить шаблонный генератор структурированного RAG-ответа при сбое соединения.
4. Зафиксировать требования к `CORSMiddleware` в спецификации API.
