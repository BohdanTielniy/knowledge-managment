# ЛР 10. Векторне сховище та семантичний пошук («Управління лісовими продуктами»)

Курс «Сховища знань та управління знаннями», ЛНУ ім. Івана Франка (2026–2027 н. р.). Гілка `lab10` репозиторію Domain Knowledge Hub.

## Статус виконання вимог

| Результат | Артефакти | Критерії C1–C4 | Статус |
|-----------|-----------|:--------------:|--------|
| **1. Корпус і метадані** | `data/corpus.jsonl`, `kb/*.md`, `docs/corpus_card.md` | C1–C4 | Готово (28 док., 213 фрагментів, 22.47 % шуму видалено, `sensitivity` для кожного) |
| **2. Стратегії chunking** | `src/chunking.py`, `docs/chunking_cmp.md`, `docs/fig_chunking_cmp.png` | C1–C4 | Готово (3 стратегії, порівняння на 10 запитах, обґрунтований вибір `by_headers`) |
| **3. Векторний індекс і embeddings** | `src/index.py`, `src/embeddings.py`, `docs/embeddings_cmp.md` | C1–C4 | Готово (2 моделі, HNSW `M`/`efSearch`, час побудови/пошуку, `upsert`/`delete` на 5 док.) |
| **4. Гібридний пошук і reranking** | `src/hybrid.py`, `docs/hybrid_report.md` | C1–C4 | Готово (BM25+Dense+RRF `k=60`, reranker `30→5`, `pre-filter`, 3 WIN + 1 LOSE) |
| **5. Золотий набір і оцінювання** | `eval/gold.jsonl`, `eval/annotator_agreement.jsonl`, `src/eval_metrics.py`, `docs/search_eval.md`, `docs/fig_eval_comparison.png` | C1–C4 | Готово (45 запитів / 6 без відповіді, $\kappa = 0.8643$, 4 конфігурації, вибір для ЛР 11) |
| **Протокол LLM і звіт** | `llm_log/`, `claims/claims.csv`, `claims/claims_summary.md`, `docs/report_lab10.md` | Розд. 6–7 | Готово |

## Запуск у Docker (рекомендовано)

Потрібен Docker (Compose v2). Усі результати (`outputs/`, `docs/*.png`, `data/corpus.jsonl`) монтуються на хост, а моделі HuggingFace кешуються у volume `hf_cache`.

```bash
cd lab10

# Збірка образу (Python 3.11 + CPU PyTorch + faiss-cpu + sentence-transformers + rank-bm25)
docker compose build

# Повний прогін усіх 5 етапів із нейромережевими моделями (multilingual-e5-small + MiniLM + CrossEncoder)
docker compose run --rm lab10

# Або швидкий автономний прогін без завантаження моделей з HuggingFace:
BACKEND=local docker compose run --rm lab10

# Запуск окремого скрипту всередині контейнера:
docker compose run --rm lab10 python3 src/eval_metrics.py --backend neural
```

## Альтернативний запуск локально (без Docker)

```bash
cd lab10
pip install -r requirements.txt
BACKEND=local bash scripts/run_all.sh     # або BACKEND=neural bash scripts/run_all.sh
```

## Середовище та версії
- **Базовий образ Docker:** `python:3.11-slim` (`seed = 42` зафіксовано в усіх скриптах)
- **Залежності (`requirements.txt`):** `torch` (CPU), `sentence-transformers>=3.0`, `faiss-cpu>=1.8`, `rank-bm25>=0.2.2`, `numpy>=1.26`, `scipy>=1.11`, `matplotlib>=3.8`
- **Безпека:** ключі API не використовуються; `restricted`-фрагменти відсікаються метаданим `pre-filter` до скорингу, усі моделі працюють локально в контейнері.
