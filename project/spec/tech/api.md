# Спецификация контрактов REST API

Контракты спроектированы в рамках методологии SDD тимлидом (Лука) и согласованы с бэкенд-разработчиком (Полина) для синхронизации серверного слоя и клиентского интерфейса (Катя). Все запросы и ответы типизированы в формате JSON.

---

## 1. Базовые параметры

- **Префикс эндпоинтов:** `/api/v1`
- **Заголовки:** `Content-Type: application/json`
- **Авторизация:** `Authorization: Bearer <jwt-token>`

---

## 2. Эндпоинты авторизации (`/auth`)

### 2.1. Регистрация
`POST /api/v1/auth/register`

- **Request:**
```json
{
  "email": "user@example.com",
  "password": "strongPassword123",
  "name": "Алексей"
}
```
- **Response (`201 Created`):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsIn...",
  "user": {
    "id": "usr_101",
    "email": "user@example.com",
    "name": "Алексей",
    "role": "user"
  }
}
```

### 2.2. Авторизация
`POST /api/v1/auth/login`

- **Request:**
```json
{
  "email": "user@example.com",
  "password": "strongPassword123"
}
```
- **Response (`200 OK`):**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsIn...",
  "user": {
    "id": "usr_101",
    "email": "user@example.com",
    "name": "Алексей",
    "role": "user"
  }
}
```

---

## 3. Эндпоинты управления аптечкой (`/kit`)

### 3.1. Получение списка лекарств в аптечке
`GET /api/v1/kit?category=Обезболивающее`

- **Response (`200 OK`):**
```json
{
  "items": [
    {
      "id": "kit_01",
      "name": "Ибупрофен",
      "dosage": "200 мг",
      "form": "таблетки",
      "category": "Обезболивающее",
      "expiry_date": "2027-05-01",
      "is_expired": false
    }
  ],
  "total": 1
}
```

### 3.2. Добавление лекарства в аптечку
`POST /api/v1/kit/items`

- **Request:**
```json
{
  "name": "Амоксициллин",
  "dosage": "500 мг",
  "form": "капсулы",
  "category": "Антибиотики",
  "expiry_date": "2028-02-15"
}
```
- **Response (`201 Created`):**
```json
{
  "id": "kit_02",
  "status": "created"
}
```

### 3.3. Удаление лекарства
`DELETE /api/v1/kit/items/{id}`
- **Response (`200 OK`):** `{"status": "deleted"}`

---

## 4. Эндпоинт интеллектуального RAG-диалога (`/chat`)

### 4.1. Отправка симптоматического запроса
`POST /api/v1/chat/query`

- **Request:**
```json
{
  "query": "Сильно болит голова и давит на виски, что принять?",
  "include_kit_context": true
}
```

- **Response (`200 OK`):**
```json
{
  "status": "success",
  "emergency_mode": false,
  "recommendation": {
    "medicine_name": "Ибупрофен",
    "in_user_kit": true,
    "dosage": "1 таблетка (200 мг) после еды. Повторный прием не ранее чем через 4-6 часов.",
    "contraindications": "Язвенная болезнь ЖКТ, тяжелая почечная недостаточность",
    "warnings": "Не превышать 1200 мг в сутки"
  },
  "sources": [
    {
      "doc_id": "doc_001",
      "title": "Инструкция ЛП-001234: Ибупрофен 200мг",
      "bm25_score": 14.82
    }
  ],
  "disclaimer": "Информация носит ознакомительный характер. При усилении симптомов обратитесь к врачу."
}
```

---

## 5. Эндпоинты администратора (`/admin`)

*(Требуют `role: "admin"`)*

### 5.1. Загрузка медицинской аннотации в корпус
`POST /api/v1/admin/corpus/upload`
- **Request:**
```json
{
  "title": "Амоксициллин 500 мг",
  "mnn": "Амоксициллин",
  "category": "Антибиотики",
  "content": "Показания: инфекции дыхательных путей... Дозировка: 500 мг 3 раза в сутки..."
}
```

### 5.2. Запуск бенчмаркинга
`GET /api/v1/admin/benchmark/metrics`
- **Response (`200 OK`):**
```json
{
  "queries_count": 45,
  "metrics": {
    "mrr": 0.842,
    "recall_at_1": 0.778,
    "recall_at_3": 0.911,
    "recall_at_5": 0.956
  }
}
```
