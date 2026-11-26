# Архитектура базы данных PostgreSQL (MedAI)

Реляционная модель данных PostgreSQL 17 с расширением `pg_trgm` для нечеткого поиска и таблицами гибридного RAG-индекса.

---

## 1. Схема сущностей и связей (ERD)

```mermaid
erDiagram
    USERS ||--o{ REFRESH_SESSIONS : "сессии обновления"
    USERS ||--o{ USER_KITS : "содержимое аптечки"
    USERS ||--o| HEALTH_PROFILES : "медицинская карта"
    USERS ||--o{ DIALOGS : "диалоги"
    DIALOGS ||--o{ MESSAGES : "сообщения"
    MESSAGES ||--o{ MESSAGE_FEEDBACK : "оценки 1..5"
    MESSAGES ||--o{ MESSAGE_REPORTS : "жалобы"
    MESSAGES ||--o{ MESSAGE_AUDIO : "озвучка"
    RAG_MEDICINES ||--o{ RAG_CHUNKS : "структурные чанки"
    RAG_CHUNKS ||--o{ RAG_POSTINGS : "инвертированный индекс"
    RAG_TERMS ||--o{ RAG_POSTINGS : "словарь термов"
    RAG_LOADS ||--o{ RAG_REVISIONS : "версионирование корпуса"

    USERS {
        uuid id PK
        text email "unique lowercase"
        text name
        text password_hash
        text role "user | admin | superadmin"
        text avatar_color
        timestamptz created_at
        timestamptz updated_at
    }

    USER_KITS {
        uuid id PK
        uuid user_id FK "on delete cascade"
        text medicine_name
        text dosage
        text form
        text category
        jsonb tags "список симптомов"
        text status "otc | rx"
        date expiry_date
        integer quantity
    }

    RAG_MEDICINES {
        text id PK "D01, D02..."
        text title "GIN pg_trgm"
        text inn "GIN pg_trgm"
        text atc_code
        text category
        jsonb forms
        jsonb indications
        jsonb contraindications
        text dosage_text
        jsonb interactions
        jsonb emergency_flags
    }

    RAG_CHUNKS {
        bigint id PK
        text doc_id FK "on delete cascade"
        integer chunk_index
        text section
        text content
        integer token_len
        jsonb embedding
    }
```

---

## 2. Миграции и наполнение

- Миграция `0001_initial_schema.py` создает базовые таблицы пользователей, аптечки, медкарты, диалогов и реестра лекарств.
- Миграция `0002_rag_hybrid_feedback_admin.py` добавляет колонку `user_kits.tags`, включает расширение `pg_trgm` с GIN-индексами по `rag_medicines.title` и `inn`, а также таблицы `rag_chunks`, `rag_terms`, `rag_postings`, `rag_stats`, `rag_loads`, `rag_revisions`, `message_feedback`, `message_reports`, `message_audio`.

```bash
make migrate
make knowledge-load DB=1
```
