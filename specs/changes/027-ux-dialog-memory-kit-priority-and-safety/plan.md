# План реализации: 027-ux-dialog-memory-kit-priority-and-safety

## Шаги
1. Исправить `PostgresSessionStore.replace_session` (сначала `INSERT` новой сессии, затем `UPDATE replaced_by`), добавить `PATCH /api/v1/auth/me`, синхронизировать подписку `user:updated` в `app.js` и скрытие `#adminQuickSwitchBtn` по умолчанию.
2. Расширить окно истории диалогов до 20 сообщений, добавить передачу `history` и `user_kit_items` в `/api/v1/chat/query`, реализовать подмешивание релевантных препаратов аптечки и корректный выбор `chosen_doc` по персональным конфликтам, а также предзагрузку контекста RAG и retry для `RateLimitError`.
3. Обновить `analyze_medicine_safety` (вес в мг/кг, возрастные группы, расширенный перечень хронических диагнозов), системный промпт `system.md`, функцию `strip_markdown` и клиентскую санитизацию `stripMarkdownForDisplay`.
4. Расширить `UpdateKitItemRequest` / хранилища аптечки, добавить `AddMedicineModal.openEdit`, бейджи сроков годности в `Kit.js`, 46 настраиваемых карточек в `Catalog.js`, справочник медкарты (62 диагноза и 45 аллергенов) и унифицировать 5 голосов TTS.
5. Исправить верстку `.kit-empty-state` и `.left-rail.collapsed`, убрать лишний подзаголовок и дефолтные подсказки в `Chat.js`, добавить unit-тесты и провести сквозную проверку в Docker Compose.
