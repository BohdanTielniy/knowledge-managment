# ЛР 11. Чат-бот на основі гібридного сховища (RAG + граф)

Курс «Сховища знань та управління знаннями», ЛНУ ім. Івана Франка (2026–2027 н. р.). Гілка `lab11` репозиторію Domain Knowledge Hub («Управління лісовими продуктами»).

## Статус виконання вимог (C1–C4)

| Результат | Артефакти | Статус |
|-----------|-----------|--------|
| **1. RAG-конвеєр із цитуванням** | `src/rag.py`, `prompts/rag_v1.md`, `outputs/rag_log.jsonl` | Готово (6 демо-запитів, 100 % валідних цитат, повний журнал) |
| **2. Підграф із графа знань** | `src/graph_context.py`, `eval/graph_questions.jsonl`, `docs/graph_vs_text.md` | Готово (entity linking + 2-hop підграф, 12 питань: покриття 9.7 % → 83.3 %) |
| **3. REST API (FastAPI)** | `api/main.py`, `docs/api.md`, `docs/openapi.json`, `scripts/test_api.py` | Готово (3 ендпоінти, 2 ролі `X-API-Key`, rate limit 429, 7/7 автотестів) |
| **4. Тестовий набір і метрики** | `eval/rag_eval.jsonl`, `eval/judge_human_agreement.jsonl`, `src/eval_rag.py`, `docs/rag_eval.md` | Готово (32 тести, 4 метрики, узгодженість суддя–людина 91.7 %, 5 провалів) |
| **5. Оптимізація «до/після»** | `docs/rag_optimization.md`, `docs/fig_rag_optimization.png` | Готово (Faithfulness 0.625 → 0.906, Abstention 0.00 → 0.75, Injection 0.00 → 1.00) |
| **Протокол LLM** | `llm_log/2026-11-24_session01.md`, `claims/claims.csv`, `claims/claims_summary.md` | Готово |

## Запуск у Docker

```bash
cd lab11
cp .env.example .env

# 1. Запустити REST API (Swagger UI: http://localhost:8000/docs)
docker compose up -d --build api

# 2. Виконати всі тести, демо та експерименти оцінювання/оптимізації
docker compose run --rm eval
```
Примітка: за замовчуванням працює локальний детермінований режим (`LLM_PROVIDER=local`, `seed=42`, без ключів API). Щоб підключити OpenAI/Groq/Ollama, розкоментуйте `LLM_PROVIDER=openai` та `LLM_API_KEY` у `.env`.
