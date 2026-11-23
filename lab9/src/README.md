# ЛР 9. Графова база знань у Neo4j («Управління лісовими продуктами»)

Курс «Сховища знань та управління знаннями», ЛНУ ім. Івана Франка. Гілка `lab09` репозиторію Domain Knowledge Hub.

## Стан
| Результат | Артефакти | Статус |
|-----------|-----------|--------|
| 1. Схема під CQ | `docs/graph_schema.png`, `docs/cq_mapping.md` | готово |
| 2. Імпорт, обмеження, індекси | `import/*.cypher`, `data/*.csv`, `scripts/run_import.sh` | скрипти готові; **вивід Neo4j ще не отримано** |
| 3. Запити Cypher | `queries/*.cypher`, `docs/cypher_results.md` | наступний крок |
| 4. GDS і PROFILE | `docs/gds_report.md` | наступний крок |
| 5. SPARQL vs Cypher, text-to-Cypher | `docs/sparql_vs_cypher.md`, `tests/t2c.jsonl` | наступний крок |
| Протокол LLM | `llm_log/`, `claims/claims.csv` | шаблони; заповнюються студентом |

## Запуск з нуля
Потрібні: Docker (Compose v2), Python 3.10+ (для скриптів перевірки).

```bash
cp .env.example .env              # задайте NEO4J_PASSWORD (>= 8 символів), .env не комітити
python3 scripts/gen_data.py       # (необов'язково) перегенерувати CSV, seed = 42
python3 scripts/check_data.py     # перевірка CSV без Neo4j + еталонні значення
docker compose up -d              # Neo4j 5.26 + GDS; перший старт довший (завантаження плагіна)
bash scripts/run_import.sh        # обмеження, імпорт, повторний імпорт, порушення обмежень
```
Neo4j Browser: http://localhost:7474 (користувач `neo4j`, пароль із `.env`). Виводи скрипту зберігаються в `outputs/` — їх вставляють у звіт.

Версії: Neo4j `neo4j:5.26-community`, GDS підбирається плагін-механізмом образу (підтвердити `RETURN gds.version()`), Python-драйвер `neo4j` 5.x (для Результатів 4–5).

## Структура
```
data/            nodes_*.csv, rels_*.csv — монтуються як file:///… у Neo4j
import/          00 обмеження та індекси, 01 вузли, 02 зв'язки, 03 кількості, 04a/b порушення
scripts/         gen_data.py, check_data.py, draw_schema.py, run_import.sh
docs/            схема, відображення CQ, примітки до даних
llm_log/ claims/ протокол «LLM-експерт»
```

## Важливо
- Дані частково **синтетичні** (140 із 166 вузлів) — декларується у звіті; див. `docs/data_notes.md`.
- Пароль і ключі API в репозиторій не потрапляють (`.env` у `.gitignore`).
- Read-only роль для text-to-Cypher (Результат 5) потребує Enterprise (`.env.example`); у Community обмеження read-only реалізується режимом сесії драйвера (`READ_ACCESS`) і перевіркою запиту.
