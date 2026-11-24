# Результат 3. Документація REST API (FastAPI)

**Реалізація:** `api/main.py`  
**OpenAPI-схема:** `docs/openapi.json` (також інтерактивний Swagger UI за адресою `http://localhost:8000/docs`)  
**Автотести:** `scripts/test_api.py` → `outputs/api_test_results.json`

## 1. Ендпоінти та автентифікація (C1–C3)

| Метод і шлях | Опис | Авторизація | Коди відповідей |
|--------------|------|-------------|-----------------|
| `GET /health` | Стан сервісу, кількість чанків корпусу й вузлів графа | Без ключа | `200 OK` |
| `POST /ask` | Питання (`question` 3–500 симв., `use_graph`, `top_k` 1–10) → відповідь, цитати, джерела, токени, затримка | `X-API-Key` | `200`, `401`, `422`, `429` |
| `GET /sources/{source_id}` | Повний текст фрагмента або властивості вузла графа з перевіркою `sensitivity` | `X-API-Key` | `200`, `401`, `403`, `404`, `429` |

**Ролі та права доступу (задаються через `.env`):**
- `public_user` (`API_KEY_PUBLIC`): доступ лише до `sensitivity = public`.
- `forester_admin` (`API_KEY_ADMIN`): повний доступ (`public`, `internal`, `restricted`).
- **Rate limit:** `RATE_LIMIT_PER_MIN = 10` запитів/хв на ключ (`429 Too Many Requests`).

## 2. Приклади запитів `curl` (C4)

```bash
# 1. Перевірка стану сервісу
curl -s http://localhost:8000/health | jq

# 2. Запит від публічної ролі (restricted автоматично виключаються pre-filter)
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-public-key" \
  -d '{"question": "Які умови високого пожежного ризику за правилом R8?", "use_graph": true, "top_k": 5}' | jq

# 3. Запит від адміністратора лісгоспу (доступ до restricted-аудиту V-102 + граф)
curl -s -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-admin-key" \
  -d '{"question": "Яке перевищення квоти виявлено на виділі V-102?", "use_graph": true, "top_k": 5}' | jq

# 4. Перевірка ізоляції прав доступу (403 Forbidden для public_user на restricted DOC-11_C01)
curl -i -H "X-API-Key: demo-public-key" http://localhost:8000/sources/DOC-11_C01

# 5. Перевірка 401 (без ключа) та 422 (невалідний запит)
curl -i -X POST http://localhost:8000/ask -H "Content-Type: application/json" -d '{"question": "Тест"}'
curl -i -X POST http://localhost:8000/ask -H "Content-Type: application/json" -H "X-API-Key: demo-public-key" -d '{"question": "a"}'
```

## 3. Результати автотестування (`scripts/test_api.py`)
Усі 7 сценаріїв пройдено на 100 %: `GET /health → 200`, без ключа `→ 401`, короткий запит `→ 422`, `public_user` бачить лише `['public']`, `forester_admin` отримує `restricted` + вузли графа, `GET /sources/DOC-11_C01` повертає `403` для `public_user` і `200` для `forester_admin`, неіснуючий ID `→ 404`, 11-й запит за хвилину `→ 429`.
