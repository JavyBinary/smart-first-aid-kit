# Спецификация контрактов REST API

Контракты API v1 строго типизированы схемами Pydantic v2 (`extra="forbid"`) и обслуживаются с обратного прокси Caddy (`/api/v1`).

---

## 1. Авторизация, сессии и CSRF (`/api/v1/auth`)

- Аутентификация: пары `HttpOnly` cookie (`access_token`, `refresh_token`) с ротацией `refresh_token` и отзывом `jti` в Redis (`RedisTokenBlacklist`).
- Защита от CSRF: `ForbiddenOriginMiddleware` отклоняет мутирующие запросы (`POST`/`PUT`/`PATCH`/`DELETE`) с заголовком `Sec-Fetch-Site: cross-site` статусом `403 Forbidden`.

| Метод и путь | Назначение | Основные поля / Ответ |
|---|---|---|
| `POST /api/v1/auth/register` | Регистрация пользователя | `{email, password, name}` $\rightarrow$ `UserResponse` + cookies |
| `POST /api/v1/auth/login` | Вход и выдача cookie-сессии | `{email, password}` $\rightarrow$ `UserResponse` + cookies |
| `POST /api/v1/auth/refresh` | Ротация access/refresh токенов | Cookie `refresh_token` $\rightarrow$ `UserResponse` |
| `POST /api/v1/auth/logout` | Выход и отзыв JWT в Redis | `200 {"status": "logged_out"}` |
| `POST /api/v1/auth/change-password` | Смена пароля и отзыв сессий | `{old_password, new_password}` |
| `GET /api/v1/auth/me` | Профиль текущего пользователя | `UserResponse {id, email, name, role, avatar_color}` |
| `PATCH /api/v1/auth/me` | Обновление имени и цвета аватара | `{name?, avatar_color?}` $\rightarrow$ `UserResponse` |
| `GET /api/v1/auth/admin/users` | Список пользователей (Admin) | `list[UserResponse]` |
| `PATCH /api/v1/auth/admin/users/{id}/role` | Смена роли `user` / `admin` (Admin) | `{role}` $\rightarrow$ `UserResponse` |

---

## 2. Домашняя аптечка (`/api/v1/kit`) и Медкарта (`/api/v1/profile`)

### 2.1. Аптечка (`/api/v1/kit`)
- `GET /api/v1/kit` $\rightarrow$ `{items: KitItem[], total: int}` (с вычисляемым полем `is_expired`).
- `POST /api/v1/kit/items`: `{id?, name, dosage, form, category, tags: string[], quantity: int >= 1, expiry: "YYYY-MM-DD", status: "otc" | "rx"}`.
- `PUT /api/v1/kit/items/{id}`: `{name?, form?, category?, tags?, dosage?, quantity?, expiry?, status?}`.
- `DELETE /api/v1/kit/items/{id}` $\rightarrow$ `200 {"status": "deleted"}`.

### 2.2. Профиль здоровья (`/api/v1/profile`)
- `GET /api/v1/profile` $\rightarrow$ `{age, weight_kg, chronic_diseases, allergies, special_notes}`.
- `PUT /api/v1/profile`: `{age?, weight_kg?, chronic_diseases?, allergies?, special_notes?}` (`age` 0..130, `weight_kg` 1..300).

---

## 3. Диалоги, SSE, оценки, жалобы и озвучка (`/api/v1`)

- `POST /api/v1/dialogs` $\rightarrow$ `201 {dialog_id}`
- `GET /api/v1/dialogs` $\rightarrow$ `{dialogs: [{dialog_id, title, created_at, updated_at}]}`
- `GET /api/v1/dialogs/{id}/messages` $\rightarrow$ `{dialog_id, title, messages: [{id, position, role, content, rag_payload, feedback, reported, created_at}]}`
- `DELETE /api/v1/dialogs/{id}` $\rightarrow$ `204`
- `POST /api/v1/dialogs/{id}/messages`: `{content, include_kit_context?, selected_pills?, response_depth?: "brief" | "detailed"}` $\rightarrow$ `202`
- `GET /api/v1/dialogs/{id}/events` — SSE (`ready`, `message_start`, `message_delta`, `message_end`, `message_error`).
- `PUT /api/v1/dialogs/{id}/messages/{msg_id}/feedback`: `{score: 1..5}` $\rightarrow$ `204`; `DELETE .../feedback` $\rightarrow$ `204`.
- `POST /api/v1/dialogs/{id}/messages/{msg_id}/report`: `{reason, comment?}` $\rightarrow$ `201 {report_id}`.
- `GET /api/v1/reports/news` $\rightarrow$ `{news: [{report_id, dialog_id, dialog_title}]}` и `POST /api/v1/reports/news/seen`: `{report_ids}`.
- `POST /api/v1/dialogs/{id}/messages/{msg_id}/audio`: `{voice}` $\rightarrow$ `202` (`{status: "ready", voice, audio_url}` с последующей отдачей MP3 по `GET .../audio?voice=...` при `SPEECH_ENABLED=true`) или `503` (если серверный TTS отключен; клиент использует fallback Web Speech API).
- `POST /api/v1/speech/synthesize`: `{text, voice}` $\rightarrow$ `200 audio/mpeg` (нейросетный синтез MP3 через `edge-tts` для 5 голосов `baya`, `kseniya`, `xenia`, `aidar`, `eugene`) или `503`.
- `POST /api/v1/chat/query`: `{query, user_kit_names?, user_kit_items?, selected_pills?, health_profile?, response_depth?, history?}` — синхронный RAG+Agent фасад для гостевого режима и резервного ответа с изоляцией истории диалога.

---

## 4. Панель администратора (`/api/v1/admin`)

Все маршруты требуют роль `admin` или `superadmin`:
- `GET /api/v1/admin/stats?period=7|30|90` $\rightarrow$ `UserStats` (счетчики, активность по дням, распределение оценок, список пользователей с `kit_count` и `medcard_filled`).
- `GET /api/v1/admin/reports?status_filter=new|resolved|dismissed|all` $\rightarrow$ `{reports}`.
- `PATCH /api/v1/admin/reports/{id}`: `{status: "resolved" | "dismissed"}` $\rightarrow$ `204`.
- `GET /api/v1/admin/medicines`, `POST /api/v1/admin/medicines`, `DELETE /api/v1/admin/medicines/{doc_id}` — управление корпусом Минздрава в PostgreSQL с горячей пересборкой индекса.
- `GET /api/v1/admin/benchmark?dataset=base|extended` $\rightarrow$ `{rows: AblationRow[]}`.
