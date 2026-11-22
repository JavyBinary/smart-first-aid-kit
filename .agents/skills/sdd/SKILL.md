---
name: sdd
description: Guides project changes through Specify, Plan, Implement, and Verify while tracking specification status in MedAI. Use when creating a feature, changing behavior, fixing a bug, or making an architectural change.
---

# SDD (Spec-Driven Development) — Регламент разработки MedAI

Разработка любых компонентов системы MedAI ведётся строго последовательно:

```text
specify -> plan -> implement -> verify
```

## Жизненный цикл изменения

1. **specify** — сформулировать и согласовать требования в `specs/changes/<change-id>/spec.md` (руководство: [references/specify.md](references/specify.md), шаблон: [references/spec-template.md](references/spec-template.md)).
2. **plan** — подготовить пошаговый инженерный план реализации в `specs/changes/<change-id>/plan.md` (руководство: [references/plan.md](references/plan.md)).
3. **implement** — реализовать план небольшими проверяемыми шагами и тестами (руководство: [references/implement.md](references/implement.md)).
4. **verify** — доказать соответствие реализации требованиям спецификации в `specs/changes/<change-id>/verification.md` (руководство: [references/verify.md](references/verify.md)).

## Управление реестром спецификаций

Центральный реестр всех изменений находится в `specs/status.yaml`.

- Создавать, обновлять и удалять записи разрешено **только** через скрипт `scripts/spec_status.py`.
- Прямое ручное редактирование файла `specs/status.yaml` запрещено.
- Подробные инструкции по работе со статусами описаны в [references/status.md](references/status.md).

## Инженерные правила перехода

- Не переходи от `specify` к `plan` и от `plan` к `implement` без явного одобрения тимлида (Лука).
- Не называй работу выполненной до успешного формирования `verification.md` и перевода статуса в `done`.
- Для Python-кода обязателен успешный прогон `make test` и проверка линтером `make lint`.
- UI-компоненты согласовываются с Катей и ведутся в выделенной ветке.
