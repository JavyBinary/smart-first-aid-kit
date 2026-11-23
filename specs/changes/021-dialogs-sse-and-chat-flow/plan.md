# 021-dialogs-sse-and-chat-flow: Инженерный план реализации

## 1. Контракты событий и брокер (`backend/src/medai/dialogs/events.py`, `event_broker.py`)
1. Определить `DialogEventType` (`message_start`, `message_delta`, `message_end`, `message_error`).
2. Описать `DialogEvent` на Pydantic v2 и протокол `DialogSubscription`.
3. Реализовать `InMemoryDialogEventBroker` с очередями `asyncio.Queue(64)`, защитой словаря подписчиков через `asyncio.Lock` и graceful close/shutdown.

## 2. Модели истории и хранилище PostgreSQL (`backend/src/medai/dialogs/history.py`, `postgres.py`)
1. Описать модели `DialogSummary`, `DialogMessage`, `DialogTranscript`, правило `make_title`.
2. Описать абстрактный интерфейс `HistoryStore`.
3. Реализовать `PostgresHistoryStore` на SQLAlchemy 2.0 Core:
   - `create_dialog(user_id) -> UUID`
   - `list_dialogs(user_id) -> list[DialogSummary]`
   - `get_transcript(user_id, dialog_id) -> DialogTranscript`
   - `delete_dialog(user_id, dialog_id) -> bool`
   - `append_exchange(user_id, dialog_id, user_msg, assistant_msg, title) -> None`

## 3. Сервисный слой и RAG-генератор (`backend/src/medai/dialogs/service.py`)
1. Сервис `DialogService` с инъекцией `HistoryStore`, `DialogEventBroker`, `InMemoryBm25Index`.
2. Реализация цепочки `asyncio.Task` для сериализации последовательных запросов в рамках одного диалога.
3. Детектор протокола неотложных состояний (Red Flags).
4. Клинический RAG-синтез на основе ранжированных документов BM25.
5. Потоковая генерация текстовых фрагментов (`message_delta`) и финализация (`message_end`).

## 4. FastAPI роутер и SSE стриминг (`backend/src/medai/dialogs/router.py`)
1. Схемы Pydantic: `SubmitMessageRequest`, `DialogResponse`, `TranscriptResponse`, `ChatQueryRequest`, `ChatQueryResponse`.
2. Эндпоинты `/api/v1/dialogs` (POST, GET).
3. Эндпоинты `/api/v1/dialogs/{id}` (DELETE), `/api/v1/dialogs/{id}/messages` (GET, POST 202).
4. Эндпоинт `/api/v1/dialogs/{id}/events` со `StreamingResponse(media_type="text/event-stream")` и keep-alive пингами.
5. Эндпоинт `/api/v1/chat/query` (POST 200) для обратной совместимости.
6. Подключение роутера в `backend/src/medai/main.py`.

## 5. Тестирование и верификация
1. Написать `backend/tests/test_dialogs.py` (тесты брокера событий, хранилища, сервиса, REST API и SSE стриминга).
2. Запустить `make test` и `make lint`.
3. Составить `verification.md` и перевести спецификацию в `done`.
