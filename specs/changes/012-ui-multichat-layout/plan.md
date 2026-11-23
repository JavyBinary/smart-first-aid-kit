# План реализации: 012-ui-multichat-layout

## Основание
Реализация спецификации `specs/changes/012-ui-multichat-layout/spec.md`.

## Порядок выполнения
1. Сформировать сетку `.app-container` в `layout.css`.
2. Реализовать методы работы с сессиями (`createSession`, `switchSession`, `deleteSession`) в `store.js`.
3. Подключить рендеринг списка сессий в `app.js`.
4. Реализовать логику табов центральной зоны.
