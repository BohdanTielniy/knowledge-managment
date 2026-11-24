# Лабораторна робота 12: OLAP-куб на основі таксономії (Domain Knowledge Hub)

- **Предметна область**: Довкілля — «Управління лісовими продуктами»
- **Студент**: Тєльний Богдан (група ФЕІ-42, ЛНУ ім. Івана Франка)
- **Версія датасету**: `1.0.0` (`seed = 42`, 1 500 рядків факту, 5 вимірів)

## Структура репозиторію (гілка `lab12`)
- `docs/star_design.md`, `sql/ddl.sql`, `docs/fig_star_schema.png` — Результат 1 (зерно, 6 бізнес-питань, зірка з таксономією IRI, SCD1/SCD2, міри).
- `etl/load.py`, `data/*.parquet`, `data/manifest.json`, `docs/data_quality_report.md` — Результат 2 (ELT, 1 500 фактів, 0 «сиріт», 7 перевірок якості).
- `sql/olap/01..09_*.sql`, `src/olap_runner.py`, `docs/olap_results.md` — Результат 3 (9 OLAP-запитів + незалежна перевірка 2 запитів у `pandas`).
- `semantic/metrics.yml`, `src/semantic_layer.py`, `docs/semantic_layer.md` — Результат 4 (6 метрик, генерація SQL, узгодженість 2 питань).
- `src/text_to_sql.py`, `tests/t2sql.jsonl`, `dashboard/*` — Результат 5 (Text-to-SQL із AST/read-only/LIMIT/timeout, 12 тестів + 3 помилки, панель із 4 візуалізаціями та 5 ризиками).
- `llm_log/`, `claims/claims.csv`, `claims/claims_summary.md` — Протокол «LLM-експерт».

## Запуск з нуля
```bash
pip install -r requirements.txt
bash scripts/run_all.sh
```
> Примітка: усі скрипти автоматично використовують **DuckDB** (`duckdb>=1.1.0`) і `sqlglot`, якщо вони встановлені, а в офлайн-середовищі без `duckdb` коректно виконують ті самі Parquet/SQL-перевірки через вбудований `sqlite3` + `pyarrow`.
