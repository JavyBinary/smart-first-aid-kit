# План реализации: 007-admin-benchmark-inspector

## Основание
Реализация спецификации `specs/changes/007-admin-benchmark-inspector/spec.md`.

## Порядок выполнения
1. Разметить модальное окно `#benchBackdrop` с сеткой метрик в `ui/admin.html`.
2. Подключить кнопку `#benchBtn` в `.stat-bar`.
3. Добавить функцию загрузки метрик с эндпоинта `/api/v1/admin/benchmark/metrics`.
4. Реализовать закрытие модалки по кнопке, фону и клавише `Escape`.
