# Руководство: Реестр спецификаций (specs/status.yaml)

Файл `specs/status.yaml` — центральный машиночитаемый реестр состояний всех спецификаций проекта MedAI.

## Формат реестра
```yaml
specs:
    - name: 001-project-scaffold
      status: done
    - name: 002-auth-rbac-system
      status: in-queue
```

## Допустимые статусы:
- `draft` — спецификация формируется, требования уточняются;
- `in-queue` — спецификация согласована тимлидом, ожидает начала работы;
- `in-progress` — по спецификации ведется активная работа (plan / implement / verify);
- `done` — верификация завершена, файл `verification.md` оформлен, тесты пройдены.

## Консольные команды управления
Запускать из корня репозитория:
```bash
python3 .agents/skills/sdd/scripts/spec_status.py create <name> [--status draft]
python3 .agents/skills/sdd/scripts/spec_status.py update <name> <status>
python3 .agents/skills/sdd/scripts/spec_status.py delete <name>
python3 .agents/skills/sdd/scripts/spec_status.py list
```

## Запреты:
- **Запрещено** редактировать `specs/status.yaml` вручную в текстовых редакторах или через потоковый ввод shell.
- **Запрещено** откатывать статус `done` в `in-progress` — новые доработки оформляются новой спецификацией.
