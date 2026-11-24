# ЛР 9. Графова база знань у Neo4j («Управління лісовими продуктами»)

Курс «Сховища знань та управління знаннями», ЛНУ ім. Івана Франка (2026–2027 н. р.). Гілка `lab09` репозиторію Domain Knowledge Hub.

## Статус виконання вимог

| Результат | Артефакти | Критерії C1–C4 | Статус |
|-----------|-----------|:--------------:|--------|
| **1. Схема під CQ** | `docs/graph_schema.png`, `docs/cq_mapping.md` | C1–C4 | Готово |
| **2. Імпорт, обмеження, індекси** | `import/*.cypher`, `data/*.csv`, `scripts/run_import.sh` | C1–C4 | Готово (CSV згенеровано; запуск у Docker закріплює вивід `outputs/`) |
| **3. Запити Cypher** | `queries/q01..q10*.cypher`, `docs/cypher_results.md`, `scripts/run_queries.sh` | C1–C4 | Готово (10 запитів, 2 аналізи впливу, ручна перевірка 3 запитів) |
| **4. GDS і PROFILE** | `queries/gds_01..02*.cypher`, `docs/gds_report.md`, `scripts/run_gds.sh` | C1–C4 | Готово (PageRank топ-10, Louvain 12 спільнот, PROFILE до/після, запис у граф) |
| **5. SPARQL vs Cypher, text-to-Cypher** | `docs/sparql_vs_cypher.md`, `tests/t2c.jsonl`, `scripts/t2c_eval.py` | C1–C4 | Готово (5 питань обома мовами, 6 критеріїв, 12 тестів T2C, 75.0 %, 3 помилки) |
| **Протокол LLM-експерта та звіт** | `llm_log/*.md`, `claims/claims.csv`, `claims/claims_summary.md`, `docs/report_lab09.md` | Розд. 6–7 | Готово |

## Середовище та версії
- **Neo4j**: `neo4j:5.26-community` (Docker Compose v2, плагін `graph-data-science`)
- **Python**: 3.10+ (`requirements.txt`: `neo4j>=5.20,<6.0`, `matplotlib>=3.8`, `python-dotenv>=1.0`)
- **Детермінованість даних**: `SEED = 42` у `scripts/gen_data.py`

## Запуск з нуля

```bash
cd lab9/src

# 1. Налаштування змінних середовища (.env не комітиться!)
cp .env.example .env              # задайте NEO4J_PASSWORD (>= 8 символів)
pip install -r requirements.txt

# 2. Генерація та автономна перевірка даних, запитів, GDS і text-to-Cypher (без Docker)
python3 scripts/gen_data.py                # генерує data/*.csv (166 вузлів, 333 зв'язки, seed=42)
python3 scripts/draw_schema.py             # генерує docs/graph_schema.png
python3 scripts/check_data.py              # перевірка цілісності CSV та еталонних сум
python3 scripts/verify_queries_and_gds.py  # перевірка CQ1–CQ10, PageRank, Louvain
python3 scripts/t2c_eval.py                # перевірка 12 тестів text-to-Cypher (read-only, схема, LIMIT)

# 3. Розгортання Neo4j 5.26 + GDS у Docker та виконання всіх етапів у живій БД
docker compose up -d
bash scripts/run_import.sh        # Результат 2: обмеження, індекси, 2х імпорт, порушення обмежень
bash scripts/run_queries.sh       # Результат 3: виконання всіх 10 запитів у outputs/queries/
bash scripts/run_gds.sh           # Результат 4: PageRank, Louvain (write) та PROFILE до/після
python3 scripts/t2c_eval.py --live # Результат 5: live-виконання text-to-Cypher у read-only режимі
```

Neo4j Browser: `http://localhost:7474` (користувач `neo4j`, пароль із `.env`).

## Структура репозиторію
```text
lab9/src/
├── compose.yaml                  # Docker Compose для Neo4j 5.26 + GDS
├── .env.example                  # Шаблон змінних середовища (без секретів)
├── requirements.txt              # Python-залежності
├── data/                         # 10 nodes_*.csv + 14 rels_*.csv (166 вузлів, 333 зв'язки)
├── import/                       # 00 обмеження/індекси, 01 вузли, 02 зв'язки, 03 лічильники, 04a/b порушення
├── queries/                      # q01..q10 (CQ1–CQ10) + gds_01 (PageRank/Louvain) + gds_02 (PROFILE)
├── tests/                        # t2c.jsonl (12 тестів text-to-Cypher)
├── scripts/                      # gen_data.py, check_data.py, draw_schema.py, verify_queries_and_gds.py, t2c_eval.py, run_*.sh
├── docs/                         # graph_schema.png, cq_mapping.md, data_notes.md, cypher_results.md, gds_report.md, sparql_vs_cypher.md, report_lab09.md
├── claims/                       # claims.csv, claims_summary.md
└── llm_log/                      # 2026-11-10_session01.md, 2026-11-23_session02.md
```

## Академічна доброчесність та безпека
- **Синтетичні дані:** 140 із 166 вузлів мають `origin = synthetic` (`source = synthetic-gen-seed42`, `confidence = 0.8`) і створені для досягнення вимог ЛР 9 ($\ge 100$ вузлів, $\ge 200$ зв'язків); див. `docs/data_notes.md`.
- **Секрети:** ключі API та паролі не зберігаються в коді й звіті (`.env` у `.gitignore`).
- **Read-only для text-to-Cypher:** у Community Edition реалізовано через `RoutingControl.READ` + статичний валідатор `validate_read_only()`; для Enterprise передбачено `CREATE ROLE`.
