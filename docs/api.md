# Спецификация контрактов REST API

Контракты спроектированы в рамках методологии SDD тимлидом (Лука) и согласованы с бэкенд-разработчиком (Полина). Все запросы и ответы типизированы в формате JSON.

---

## 1. Базовые параметры

- **Префикс эндпоинтов:** `/api/v1`
- **Базовый URL клиента:** `http://localhost:8000/api/v1`
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

### 2.3. Смена пароля
`POST /api/v1/auth/change-password`
- **Request:**
```json
{
  "old_password": "strongPassword123",
  "new_password": "newStrongPassword456"
}
```
- **Response (`200 OK`):**
```json
{
  "status": "success",
  "message": "Пароль успешно обновлен"
}
```

---

## 3. Эндпоинты управления аптечкой (`/kit`)

### 3.1. Получение списка медикаментов
`GET /api/v1/kit`
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
      "tags": ["боль", "воспаление", "жар"],
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
  "tags": ["антибиотик", "инфекции", "ангина"]
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
- **Response (`200 OK`):**
```json
{
  "status": "deleted"
}
```

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
      "doc_id": "D01",
      "title": "Инструкция ЛП-001234: Ибупрофен 200мг",
      "bm25_score": 14.82
    }
  ],
  "disclaimer": "Информация носит ознакомительный характер. При усилении симптомов обратитесь к врачу."
}
```

---

## 5. Эндпоинты администратора (`/admin`)

### 5.1. Получение списка медицинских инструкций
`GET /api/v1/admin/corpus`
- **Response (`200 OK`):**
```json
{
  "items": [
    {
      "id": "D01",
      "name": "Ибупрофен",
      "category": "НПВП",
      "annotation": "Нестероидный противовоспалительный препарат..."
    }
  ],
  "total": 1
}
```

### 5.2. Добавление медицинской аннотации в корпус
`POST /api/v1/admin/corpus/upload`
- **Request:**
```json
{
  "title": "Амоксициллин 500 мг",
  "category": "Антибиотики",
  "annotation": "Антибактериальное средство широкого спектра действия..."
}
```
- **Response (`201 Created`):**
```json
{
  "id": "D_new",
  "status": "created"
}
```

### 5.3. Метрики качества поискового ядра
`GET /api/v1/admin/benchmark/metrics`
- **Response (`200 OK`):**
```json
{
  "queries_count": 15,
  "metrics": {
    "mrr": 0.842,
    "recall_at_1": 0.778,
    "recall_at_3": 0.911,
    "recall_at_5": 0.956,
    "latency_p95_ms": 12.4
  }
}
```
