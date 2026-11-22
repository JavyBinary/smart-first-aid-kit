# План реализации: 008-sdd-foundation-reorganization

## Основание
Реализация спецификации `specs/changes/008-sdd-foundation-reorganization/spec.md`.

## Порядок выполнения
1. Развернуть инфраструктуру `.agents/skills/sdd/` со скриптом `spec_status.py` и шаблонами.
2. Создать каталог `docs/` и перенести актуальную архитектурную документацию.
3. Оформить историю выполненных работ в виде спецификаций 001–007 в `specs/changes/`.
4. Сформировать реестр `specs/status.yaml` и подтвердить его целостность через `spec_status.py list`.
5. Создать `Makefile` с командами сборки, запуска и тестирования.
6. Обновить регламенты `AGENTS.md`, `GEMINI.md`, `README.md` и журнал `CHANGE_HISTORY.md`.
