# Архитектура базы данных PostgreSQL (MedAI)

Реляционная модель данных для серверного контура умной аптечки MedAI (кафедра ИУ5 МГТУ им. Н. Э. Баумана).

---

## 1. Схема сущностей и связей (ERD)

```mermaid
erDiagram
    USERS ||--o{ REFRESH_SESSIONS : "сессии обновления"
    USERS ||--o{ USER_KITS : "содержимое аптечки"
    USERS ||--o| HEALTH_PROFILES : "медицинская карта"
    USERS ||--o{ DIALOGS : "консультационные сессии"
    DIALOGS ||--o{ MESSAGES : "сообщения"
    RAG_MEDICINES ||--o| RAG_BM25_INDEX : "инвертированный индекс"

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

    REFRESH_SESSIONS {
        uuid id PK
        uuid user_id FK "on delete cascade"
        uuid family_id
        bytea token_hash "unique sha256"
        timestamptz created_at
        timestamptz expires_at
        timestamptz revoked_at
        uuid replaced_by FK
    }

    USER_KITS {
        uuid id PK
        uuid user_id FK "on delete cascade"
        text medicine_name
        text dosage
        text form
        text category
        text status "otc | rx"
        date expiry_date
        integer quantity
        text notes
        text icon_color
        timestamptz created_at
        timestamptz updated_at
    }

    HEALTH_PROFILES {
        uuid id PK
        uuid user_id FK "unique on delete cascade"
        integer age
        float weight_kg
        jsonb chronic_diseases
        jsonb allergies
        text special_notes
        timestamptz created_at
        timestamptz updated_at
    }

    DIALOGS {
        uuid id PK
        uuid user_id FK "on delete cascade"
        text title
        timestamptz created_at
        timestamptz updated_at
    }

    MESSAGES {
        bigint id PK
        uuid dialog_id FK "on delete cascade"
        integer position
        text role "user | assistant | system"
        text content
        jsonb rag_payload
        timestamptz created_at
    }

    RAG_MEDICINES {
        text id PK "D01, D02..."
        text title
        text inn
        text atc_code
        text category
        jsonb forms
        jsonb indications
        jsonb contraindications
        text dosage_text
        jsonb interactions
        jsonb emergency_flags
        timestamptz created_at
        timestamptz updated_at
    }

    RAG_BM25_INDEX {
        text doc_id PK, FK "on delete cascade"
        text lemmatized_text
        integer doc_length
        jsonb term_frequencies
        timestamptz updated_at
    }
```

---

## 2. Инварианты безопасности и целостности
1. **Каскадное удаление данных:** При удалении пользователя каскадно удаляются сессии, аптечка, медкарта и диалоги (`ON DELETE CASCADE`).
2. **Безопасность параметров SQL:** В модуле `engine.py` флаг `hide_parameters=True` гарантирует, что пароли и токены не попадут в текст логов или исключений при сбоях.
3. **Хранение токенов:** Токены сессий хранятся в бинарном поле `LargeBinary` в виде дайджестов SHA-256. В открытом виде токены в базе никогда не сохраняются.
4. **Контроль ролей:** Допустимые значения ролей зафиксированы констрейнтом `users_role_valid` (`user`, `admin`, `superadmin`). Роль `superadmin` обладает иммунитетом от удаления.
