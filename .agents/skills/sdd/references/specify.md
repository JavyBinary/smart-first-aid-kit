# Руководство: Фаза Specify (Формулирование спецификации)

На этапе `specify` агент фиксирует требования, ограничения и критерии приёмки до написания какого-либо программного кода.

## Правила этапа:
1. Создать новую директорию изменения `specs/changes/<change-id>/`.
2. Создать файл `specs/changes/<change-id>/spec.md` по шаблону [spec-template.md](spec-template.md).
3. Добавить запись в реестр со статусом `draft` с помощью команды:
   ```bash
   python3 .agents/skills/sdd/scripts/spec_status.py create <change-id> --status draft
   ```
4. Требования должны формулироваться с уникальными идентификаторами `REQ-001`, `REQ-002` и т.д.
5. Для каждого ключевого требования обязателен BDD-сценарий (Given / When / Then).
6. Никакой код и автоматические тесты на этапе `specify` **не создаются**.
7. После согласования спецификации с тимлидом (Лука) статус переводится в `in-queue`:
   ```bash
   python3 .agents/skills/sdd/scripts/spec_status.py update <change-id> in-queue
   ```
