# Спецификация контрактов REST API

Контракты спроектированы в рамках методологии SDD тимлидом (Лука) и согласованы с бэкенд-разработчиком (Полина) для синхронизации серверного слоя и клиентского интерфейса (Катя). Все запросы и ответы типизированы в формате JSON.

---

## 1. Базовые параметры

- **Префикс эндпоинтов:** `/api/v1`
- **Базовый URL клиента:** `http://localhost:8000/api/v1`
- **Заголовки:** `Content-Type: application/json`
- **Авторизация:** `Authorization: Bearer <jwt-token>`

### 1.1. Клиентская интеграция и архитектура Seamless Fallback

Для обеспечения параллельной независимой разработки клиентского интерфейса (Катя) и серверного слоя FastAPI (Полина) на стороне клиента реализована стратегия **Seamless Fallback (двойной режим)**:
1. **Базовый URL:** `http://localhost:8000/api/v1` (дефолтный хост сервера Uvicorn).
2. **Обязательное требование к FastAPI (Полина):** настроить `CORSMiddleware`, чтобы браузер не блокировал кросс-доменные запросы от локальных страниц интерфейса:
   ```python
   from fastapi.middleware.cors import CORSMiddleware

   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```
3. **Принцип работы двойного режима:**
   - Клиентские сценарии (`auth.html`, `site.html`, `admin.html`) в первую очередь отправляют реальный HTTP-запрос к эндпоинтам FastAPI.
   - Если сервер бэкенда не запущен (`Failed to fetch`), клиент перехватывает исключение в блоке `catch` и плавно переходит в локальный демонстрационный режим с формированием данных идентичной Pydantic-структуры.
   - **Интеграционный эффект:** при запуске бэкенда Полины интерфейс Каты не требует удаления мок-данных или переписывания кода — он автоматически подхватывает живую базу данных PostgreSQL и генерации LLM.

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

- **Headers:** `Authorization: Bearer <jwt-token>`
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
  "tags": ["антибиотик", "инфекции", "ангина"],
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

### 5.1. Получение списка инструкций корпуса
`GET /api/v1/admin/corpus`
- **Response (`200 OK`):**
```json
{
  "items": [
    {
      "id": "doc_01",
      "name": "Парацетамол",
      "category": "Анальгетики и антипиретики",
      "annotation": "Симптоматическое лечение лихорадочного синдрома, болевого синдрома..."
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
  "mnn": "Амоксициллин",
  "category": "Антибиотики",
  "content": "Показания: инфекции дыхательных путей... Дозировка: 500 мг 3 раза в сутки..."
}
```
- **Response (`201 Created`):**
```json
{
  "id": "doc_new",
  "status": "created"
}
```

### 5.3. Удаление инструкции из корпуса
`DELETE /api/v1/admin/corpus/{id}`
- **Response (`200 OK`):**
```json
{
  "status": "deleted"
}
```

### 5.4. Получение метрик бенчмаркинга
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
