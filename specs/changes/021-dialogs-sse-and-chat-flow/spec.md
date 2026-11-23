# 021-dialogs-sse-and-chat-flow: История диалогов, брокер событий и потоковая передача SSE

## Цель
Реализовать асинхронный серверный диалоговый слой MedAI в соответствии со стандартом НИРС МГТУ им. Н. Э. Баумана: персистентность истории в PostgreSQL (`dialogs`, `messages`), внутрипроцессный брокер событий `InMemoryDialogEventBroker` с очередями с ограниченной емкостью, фоновую цепочку задач RAG-генерации с поддержкой протокола Red Flags (неотложная помощь), потоковый SSE-эндпоинт (`GET /api/v1/dialogs/{id}/events`), контракт `POST 202 /api/v1/dialogs/{id}/messages` и синхронный фасад `POST /api/v1/chat/query`.

## Допущения и контекст
- Сервер связывает HTTP API с поисковым BM25-ядром `InMemoryBm25Index` из этапа 4 и схемой базы данных `0001_initial_schema`.
- Запись сообщений в PostgreSQL выполняется атомарно после завершения генерации; незавершенные из-за ошибки генерации не засоряют историю.
- Брокер событий изолирован от FastAPI и хранилища; медленные клиенты или переполненные очереди (64 события) отключаются без создания backpressure на генератор.
- Разделение ответственности:
  - Лука (Тимлид): архитектура брокера событий, связка с BM25, верификация.
  - Полина: REST/SSE эндпоинты, SQLAlchemy-хранилище `PostgresHistoryStore`.
  - Катя: клиентский чат-интерфейс в `frontend/src/components/Chat.js`.

## Требования
- **REQ-001:** Создать модуль `backend/src/medai/dialogs/events.py` с типами событий `DialogEventType` (`message_start`, `message_delta`, `message_end`, `message_error`), моделью `DialogEvent` (Pydantic v2) и протоколом `DialogSubscription`.
- **REQ-002:** Создать брокер событий `backend/src/medai/dialogs/event_broker.py` с классом `InMemoryDialogEventBroker` (очереди на 64 события, методы `subscribe`, `unsubscribe`, `publish`, `close_dialog`, `shutdown`, защита от блокировок через `asyncio.Lock`).
- **REQ-003:** Реализовать модели данных и интерфейс хранилища `backend/src/medai/dialogs/history.py` (`DialogSummary`, `DialogMessage`, `DialogTranscript`, `HistoryStore`). Название диалога формируется из первого пользовательского сообщения (длина до 80 символов, схлопывание пробелов).
- **REQ-004:** Реализовать `PostgresHistoryStore` в `backend/src/medai/dialogs/postgres.py`, выполняющий CRUD-операции над таблицами `dialogs` и `messages` через SQLAlchemy 2.0 Core с проверкой прав владельца `user_id`.
- **REQ-005:** Реализовать сервисный слой `backend/src/medai/dialogs/service.py` (`DialogService`):
  - Последовательная цепочка фоновых задач `asyncio.Task` для каждого `dialog_id`.
  - Интеграция с BM25 поиском `InMemoryBm25Index`.
  - Триаж неотложных состояний (Red Flags: ожоги, артериальное кровотечение, удушье, судороги, потеря сознания) с выставлением `emergency_mode=True`.
  - Потоковая публикация дельт в брокер событий.
  - Атомарное сохранение пользовательского и ассистентского сообщений.
- **REQ-006:** Создать FastAPI роутер `backend/src/medai/dialogs/router.py`:
  - `POST /api/v1/dialogs` — создание нового диалога (`201 Created` с заголовком `Location`).
  - `GET /api/v1/dialogs` — постраничный список диалогов пользователя.
  - `GET /api/v1/dialogs/{id}/messages` — получение стенограммы сообщений диалога.
  - `DELETE /api/v1/dialogs/{id}` — удаление диалога (`204 No Content`).
  - `POST /api/v1/dialogs/{id}/messages` — постановка запроса в очередь (`202 Accepted`).
  - `GET /api/v1/dialogs/{id}/events` — Server-Sent Events (SSE) поток (`text/event-stream`, `ready`, дельты, `keep-alive`, `message_end`).
  - `POST /api/v1/chat/query` — синхронный JSON-эндпоинт RAG-поиска для прямой совместимости с текущим фронтендом.
- **REQ-007:** Защита доступа: все методы диалогов требуют аутентифицированного пользователя (`user_id`). Попытка доступа к чужому или несуществующему диалогу возвращает `404 Not Found`.

## Сценарии взаимодействия (BDD)

### Сценарий 1: Создание диалога и отправка сообщения с получением SSE-потока
- **Given** авторизованный пользователь с валидным JWT Access токеном
- **When** клиент вызывает `POST /api/v1/dialogs`, подключается к `GET /api/v1/dialogs/{id}/events` и отправляет `POST /api/v1/dialogs/{id}/messages` с текстом *"Болит зуб, что принять?"*
- **Then** сервер возвращает `202 Accepted`, клиент получает по SSE событие `message_start`, последовательность `message_delta` с текстом рекомендации (например, Ибупрофен) и `message_end` с метаданными источников BM25. Сообщения сохраняются в PostgreSQL.

### Сценарий 2: Отработка протокола Red Flags (Неотложная помощь)
- **Given** активный диалог
- **When** пользователь отправляет сообщение *"Термический ожог кипятком руки, кожа вздулась пузырями"*
- **Then** система мгновенно идентифицирует маркеры неотложного состояния, устанавливает `emergency_mode=true`, возвращает алгоритм первой доврачебной помощи (охлаждение водой, запрет нанесения масел) и предупреждение о вызове 112/103.

### Сценарий 3: Защита от утечки чужих диалогов (Multi-tenancy Isolation)
- **Given** два зарегистрированных пользователя User A и User B
- **When** User B отправляет запрос `GET /api/v1/dialogs/{id_A}/messages` к диалогу User A
- **Then** сервер возвращает `404 Not Found`, данные User A остаются изолированными.
