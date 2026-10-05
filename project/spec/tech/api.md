# Спецификация контрактов API (REST API Contracts)

Спецификация разработана для синхронизации работы бэкенда (Полина) и фронтенда (Катя). Описывает форматы запросов и ответов REST API.

---

## 1. Общие соглашения

- **Базовый URL:** `/api/v1`
- **Формат обмена данными:** `Content-Type: application/json; charset=utf-8`
- **Аутентификация:** Bearer Token (JWT в заголовке `Authorization: Bearer <token>`)
- **Стандартные коды ответов:**
  - `200 OK` — успешный запрос.
  - `201 Created` — ресурс успешно создан.
  - `400 Bad Request` — ошибка валидации входных данных.
  - `401 Unauthorized` — отсутствует или невалиден токен сессии.
  - `403 Forbidden` — недостаточно прав (доступно только Администратору).
  - `404 Not Found` — запрашиваемый ресурс не найден.
  - `500 Internal Server Error` — внутренняя ошибка сервера.

---

## 2. Модуль аутентификации (`/auth`)

### 2.1. Регистрация нового пользователя
- **Метод:** `POST /api/v1/auth/register`
- **Тело запроса (Request Body):**
```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "name": "Алексей Иванов"
}
```
- **Успешный ответ (Response `201 Created`):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "usr_9981",
    "email": "user@example.com",
    "name": "Алексей Иванов",
    "role": "user"
  }
}
```

### 2.2. Вход в систему (Авторизация)
- **Метод:** `POST /api/v1/auth/login`
- **Тело запроса:**
```json
{
  "email": "admin@medai.ru",
  "password": "adminPassword123"
}
```
- **Успешный ответ (Response `200 OK`):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "adm_0001",
    "email": "admin@medai.ru",
    "name": "Тимур (Куратор базы)",
    "role": "admin"
  }
}
```

---

## 3. Модуль управления домашней аптечкой (`/kit`)

### 3.1. Получение списка лекарств в аптечке
- **Метод:** `GET /api/v1/kit`
- **Параметры строки запроса:** `category` (опционально, фильтр по тегу), `search` (опционально)
- **Успешный ответ (Response `200 OK`):**
```json
{
  "total_items": 3,
  "items": [
    {
      "id": "med_101",
      "name": "Ибупрофен",
      "dosage": "200 мг",
      "form": "таблетки",
      "category": "Обезболивающее",
      "expiry_date": "2027-05-01",
      "is_expired": false,
      "created_at": "2026-10-01T12:00:00Z"
    },
    {
      "id": "med_102",
      "name": "Дротаверин",
      "dosage": "40 мг",
      "form": "таблетки",
      "category": "ЖКТ",
      "expiry_date": "2026-12-01",
      "is_expired": false,
      "created_at": "2026-10-01T12:05:00Z"
    }
  ]
}
```

### 3.2. Добавление лекарства в аптечку
- **Метод:** `POST /api/v1/kit/items`
- **Тело запроса:**
```json
{
  "name": "Парацетамол",
  "dosage": "500 мг",
  "form": "таблетки",
  "category": "От простуды",
  "expiry_date": "2028-01-15"
}
```
- **Успешный ответ (Response `201 Created`):**
```json
{
  "id": "med_103",
  "name": "Парацетамол",
  "category": "От простуды",
  "status": "added"
}
```

### 3.3. Удаление лекарства из аптечки
- **Метод:** `DELETE /api/v1/kit/items/{item_id}`
- **Успешный ответ (Response `200 OK`):**
```json
{
  "status": "deleted",
  "id": "med_101"
}
```

---

## 4. Модуль интеллектуального диалога и RAG (`/chat`)

### 4.1. Отправка симптоматического запроса
- **Метод:** `POST /api/v1/chat/query`
- **Тело запроса:**
```json
{
  "query": "Сильно болит голова и давит на виски, что принять?",
  "include_kit_context": true
}
```
- **Успешный ответ (Response `200 OK`):**
```json
{
  "query_id": "req_88123",
  "status": "success",
  "emergency_mode": false,
  "recommendation": {
    "recommended_medicine": "Ибупрофен",
    "in_user_kit": true,
    "dosage_regimen": "1 таблетка (200 мг) после еды. Максимум 3 раза в сутки.",
    "pharmacological_action": "НПВП, оказывает выраженное анальгезирующее и противовоспалительное действие.",
    "contraindications": ["Язва желудка в стадии обострения", "Тяжелая почечная недостаточность", "III триместр беременности"],
    "alternative_medicines": ["Парацетамол (нет в аптечке)"]
  },
  "retrieved_sources": [
    {
      "doc_id": "doc_ibuprofen_200",
      "title": "Инструкция по медицинскому применению: Ибупрофен 200мг",
      "bm25_score": 14.82,
      "source_url": "https://grls.rosminzdrav.ru/Grls_View_v2.aspx?routingGuid=..."
    }
  ],
  "disclaimer": "Внимание! Рекомендация носит вспомогательный характер. Если симптомы не проходят в течение 48 часов, обязательно обратитесь к врачу."
}
```

---

## 5. Модуль администрирования корпуса (`/admin`)

*(Доступно только для пользователей с ролью `role: "admin"`)*

### 5.1. Загрузка медицинской инструкции в корпус
- **Метод:** `POST /api/v1/admin/corpus/upload`
- **Тело запроса:**
```json
{
  "title": "Амоксициллин 500 мг (капсулы)",
  "mnn": "Амоксициллин",
  "category": "Антибиотики",
  "content": "Показания: инфекции дыхательных путей... Дозировка: 500 мг 3 раза в день... Противопоказания: гиперчувствительность к пенициллинам..."
}
```

### 5.2. Запуск переиндексации BM25
- **Метод:** `POST /api/v1/admin/index/rebuild`
- **Успешный ответ (Response `200 OK`):**
```json
{
  "status": "indexed",
  "total_documents": 143,
  "vocabulary_size": 4832,
  "average_document_length": 182.4,
  "indexing_time_ms": 38.6
}
```

### 5.3. Запуск расчета метрик качества (Бенчмарк)
- **Метод:** `GET /api/v1/admin/benchmark/metrics`
- **Успешный ответ (Response `200 OK`):**
```json
{
  "total_test_queries": 45,
  "metrics": {
    "mrr": 0.842,
    "recall_at_1": 0.778,
    "recall_at_3": 0.911,
    "recall_at_5": 0.956
  },
  "evaluated_at": "2026-10-05T09:00:00Z"
}
```
