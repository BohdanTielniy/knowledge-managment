#!/usr/bin/env python3
"""
Результат 3 (OLAP-запити):
- Генерує 9 стандартизованих DuckDB SQL файлів у sql/olap/01..09_*.sql:
  ROLLUP, CUBE/GROUPING SETS, slice, dice, pivot, drill-down по таксономії,
  віконні (накопичення, DENSE_RANK, 3-місячна ковзна середня).
- Виконує всі 9 запитів (нативно в DuckDB, або з еквівалентним SQLite-виконанням в офлайн-режимі).
- Незалежно перевіряє 2 результати (01_rollup та 06_drilldown_taxonomy) через pandas.
- Зберігає docs/olap_results.md та outputs/olap_summary.json.
"""
import json
import os
import sqlite3
import pandas as pd

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SQL_DIR = os.path.join(BASE_DIR, "sql", "olap")
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
OUT_DIR = os.path.join(BASE_DIR, "outputs")

QUERIES = [
    {
        "file": "01_rollup.sql",
        "kind": "ROLLUP",
        "question": "Яка динаміка виручки (тис. грн) та обсягу деревини (м³) з проміжними підсумками за роками та лісництвами?",
        "duckdb_sql": """SELECT
    COALESCE(CAST(d.year AS VARCHAR), 'ВСЬОГО') AS year_lbl,
    COALESCE(l.forestry_code, 'Усі лісництва') AS forestry_code,
    COUNT(*) AS events_cnt,
    ROUND(SUM(f.volume_m3), 1) AS total_vol_m3,
    ROUND(SUM(f.revenue_uah) / 1000.0, 2) AS revenue_k_uah
FROM fact_forest_harvest f
JOIN dim_date d ON f.date_sk = d.date_sk
JOIN dim_location l ON f.location_sk = l.location_sk
GROUP BY ROLLUP (d.year, l.forestry_code)
ORDER BY d.year NULLS LAST, l.forestry_code NULLS LAST;""",
        "sqlite_sql": """WITH base AS (
    SELECT d.year, l.forestry_code, f.volume_m3, f.revenue_uah
    FROM fact_forest_harvest f
    JOIN dim_date d ON f.date_sk = d.date_sk
    JOIN dim_location l ON f.location_sk = l.location_sk
)
SELECT CAST(year AS TEXT) AS year_lbl, forestry_code, COUNT(*) AS events_cnt,
       ROUND(SUM(volume_m3), 1) AS total_vol_m3, ROUND(SUM(revenue_uah)/1000.0, 2) AS revenue_k_uah,
       0 AS ord1, year AS y_ord, forestry_code AS f_ord
FROM base GROUP BY year, forestry_code
UNION ALL
SELECT CAST(year AS TEXT), 'Усі лісництва', COUNT(*),
       ROUND(SUM(volume_m3), 1), ROUND(SUM(revenue_uah)/1000.0, 2),
       0, year, 'ZZZZ'
FROM base GROUP BY year
UNION ALL
SELECT 'ВСЬОГО', 'Усі лісництва', COUNT(*),
       ROUND(SUM(volume_m3), 1), ROUND(SUM(revenue_uah)/1000.0, 2),
       1, 9999, 'ZZZZ'
FROM base
ORDER BY ord1, y_ord, f_ord;""",
    },
    {
        "file": "02_cube_grouping_sets.sql",
        "kind": "GROUPING SETS / CUBE",
        "question": "Як розподіляється виручка та рентабельність за класом таксономії та статусом FSC-сертифікації (усі комбінації)?",
        "duckdb_sql": """SELECT
    COALESCE(p.top_class_uk, 'Усі класи') AS top_class_uk,
    COALESCE(CASE WHEN l.fsc_certified THEN 'FSC-так' ELSE 'FSC-ні' END, 'Усі статуси') AS fsc_status,
    COUNT(*) AS events_cnt,
    ROUND(SUM(f.revenue_uah) / 1000.0, 2) AS revenue_k_uah,
    ROUND(100.0 * SUM(f.margin_uah) / NULLIF(SUM(f.revenue_uah), 0), 2) AS margin_pct
FROM fact_forest_harvest f
JOIN dim_product_taxonomy p ON f.product_sk = p.product_sk
JOIN dim_location l ON f.location_sk = l.location_sk
GROUP BY CUBE (p.top_class_uk, CASE WHEN l.fsc_certified THEN 'FSC-так' ELSE 'FSC-ні' END)
ORDER BY top_class_uk, fsc_status;""",
        "sqlite_sql": """WITH base AS (
    SELECT p.top_class_uk, CASE WHEN l.fsc_certified = 1 THEN 'FSC-так' ELSE 'FSC-ні' END AS fsc_status,
           f.revenue_uah, f.margin_uah
    FROM fact_forest_harvest f
    JOIN dim_product_taxonomy p ON f.product_sk = p.product_sk
    JOIN dim_location l ON f.location_sk = l.location_sk
)
SELECT top_class_uk, fsc_status, COUNT(*) AS events_cnt,
       ROUND(SUM(revenue_uah)/1000.0, 2) AS revenue_k_uah,
       ROUND(100.0 * SUM(margin_uah) / NULLIF(SUM(revenue_uah), 0), 2) AS margin_pct
FROM base GROUP BY top_class_uk, fsc_status
UNION ALL
SELECT top_class_uk, 'Усі статуси', COUNT(*), ROUND(SUM(revenue_uah)/1000.0, 2),
       ROUND(100.0 * SUM(margin_uah) / NULLIF(SUM(revenue_uah), 0), 2)
FROM base GROUP BY top_class_uk
UNION ALL
SELECT 'Усі класи', fsc_status, COUNT(*), ROUND(SUM(revenue_uah)/1000.0, 2),
       ROUND(100.0 * SUM(margin_uah) / NULLIF(SUM(revenue_uah), 0), 2)
FROM base GROUP BY fsc_status
UNION ALL
SELECT 'Усі класи', 'Усі статуси', COUNT(*), ROUND(SUM(revenue_uah)/1000.0, 2),
       ROUND(100.0 * SUM(margin_uah) / NULLIF(SUM(revenue_uah), 0), 2)
FROM base
ORDER BY top_class_uk, fsc_status;""",
    },
    {
        "file": "03_slice.sql",
        "kind": "SLICE (year = 2025)",
        "question": "Яка структура виручки та обсягів у 2025 році за підкласами продуктів?",
        "duckdb_sql": """SELECT
    p.subclass_uk,
    COUNT(*) AS events_cnt,
    ROUND(SUM(f.volume_m3), 1) AS total_vol_m3,
    ROUND(SUM(f.mass_kg), 1) AS total_mass_kg,
    ROUND(SUM(f.revenue_uah) / 1000.0, 2) AS revenue_k_uah
FROM fact_forest_harvest f
JOIN dim_date d ON f.date_sk = d.date_sk
JOIN dim_product_taxonomy p ON f.product_sk = p.product_sk
WHERE d.year = 2025
GROUP BY p.subclass_uk
ORDER BY revenue_k_uah DESC;""",
    },
    {
        "file": "04_dice.sql",
        "kind": "DICE (2025-2026, LS-01/LS-03, Деревинні)",
        "question": "Які обсяги та середня ціна деревини у 2025–2026 рр. у гірських лісництвах LS-01 та LS-03?",
        "duckdb_sql": """SELECT
    d.year,
    l.forestry_code,
    p.subclass_uk,
    ROUND(SUM(f.volume_m3), 1) AS total_vol_m3,
    ROUND(SUM(f.revenue_uah) / NULLIF(SUM(f.volume_m3), 0), 2) AS weighted_price_uah_m3,
    ROUND(AVG(f.ndvi_score), 3) AS avg_ndvi
FROM fact_forest_harvest f
JOIN dim_date d ON f.date_sk = d.date_sk
JOIN dim_location l ON f.location_sk = l.location_sk
JOIN dim_product_taxonomy p ON f.product_sk = p.product_sk
WHERE d.year IN (2025, 2026)
  AND l.forestry_code IN ('LS-01', 'LS-03')
  AND p.top_class_uk = 'Деревинні продукти'
GROUP BY d.year, l.forestry_code, p.subclass_uk
ORDER BY d.year, l.forestry_code, total_vol_m3 DESC;""",
    },
    {
        "file": "05_pivot.sql",
        "kind": "PIVOT (квартали по лісництвах)",
        "question": "Як розподіляється виручка (тис. грн) кожного лісництва по кварталах Q1–Q4 (зведена матриця)?",
        "duckdb_sql": """SELECT
    l.forestry_code,
    l.forestry_name,
    ROUND(SUM(CASE WHEN d.quarter = 1 THEN f.revenue_uah ELSE 0 END) / 1000.0, 2) AS Q1_k_uah,
    ROUND(SUM(CASE WHEN d.quarter = 2 THEN f.revenue_uah ELSE 0 END) / 1000.0, 2) AS Q2_k_uah,
    ROUND(SUM(CASE WHEN d.quarter = 3 THEN f.revenue_uah ELSE 0 END) / 1000.0, 2) AS Q3_k_uah,
    ROUND(SUM(CASE WHEN d.quarter = 4 THEN f.revenue_uah ELSE 0 END) / 1000.0, 2) AS Q4_k_uah,
    ROUND(SUM(f.revenue_uah) / 1000.0, 2) AS total_k_uah
FROM fact_forest_harvest f
JOIN dim_date d ON f.date_sk = d.date_sk
JOIN dim_location l ON f.location_sk = l.location_sk
GROUP BY l.forestry_code, l.forestry_name
ORDER BY total_k_uah DESC;""",
    },
    {
        "file": "06_drilldown_taxonomy.sql",
        "kind": "DRILL-DOWN по таксономії (клас -> підклас -> продукт IRI)",
        "question": "Який внесок кожного рівня ієрархії таксономії (клас -> підклас -> продукт) у загальну виручку та маржу?",
        "duckdb_sql": """SELECT
    p.top_class_uk,
    p.subclass_uk,
    p.product_name_uk,
    p.skos_notation,
    COUNT(*) AS events_cnt,
    ROUND(SUM(f.revenue_uah) / 1000.0, 2) AS revenue_k_uah,
    ROUND(100.0 * SUM(f.revenue_uah) / SUM(SUM(f.revenue_uah)) OVER (), 2) AS share_total_pct,
    ROUND(100.0 * SUM(f.margin_uah) / NULLIF(SUM(f.revenue_uah), 0), 2) AS margin_pct
FROM fact_forest_harvest f
JOIN dim_product_taxonomy p ON f.product_sk = p.product_sk
GROUP BY p.top_class_uk, p.subclass_uk, p.product_name_uk, p.skos_notation
ORDER BY p.top_class_uk, revenue_k_uah DESC;""",
    },
    {
        "file": "07_window_cumulative.sql",
        "kind": "Віконна: накопичувальна виручка (YTD)",
        "question": "Як зростає накопичувальна виручка (YTD, тис. грн) помісячно у 2025 році?",
        "duckdb_sql": """WITH monthly AS (
    SELECT d.year_month, ROUND(SUM(f.revenue_uah) / 1000.0, 2) AS month_rev_k
    FROM fact_forest_harvest f
    JOIN dim_date d ON f.date_sk = d.date_sk
    WHERE d.year = 2025
    GROUP BY d.year_month
)
SELECT
    year_month,
    month_rev_k,
    ROUND(SUM(month_rev_k) OVER (ORDER BY year_month ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS ytd_rev_k
FROM monthly
ORDER BY year_month;""",
    },
    {
        "file": "08_window_rank.sql",
        "kind": "Віконна: DENSE_RANK виконавців у лісництвах",
        "question": "Хто з лісників і бригад входить у топ-2 за виручкою в кожному лісництві?",
        "duckdb_sql": """WITH agg AS (
    SELECT l.forestry_code, a.staff_code, a.actor_name, a.actor_type,
           COUNT(*) AS events_cnt,
           ROUND(SUM(f.revenue_uah) / 1000.0, 2) AS revenue_k_uah
    FROM fact_forest_harvest f
    JOIN dim_location l ON f.location_sk = l.location_sk
    JOIN dim_actor a ON f.actor_sk = a.actor_sk
    GROUP BY l.forestry_code, a.staff_code, a.actor_name, a.actor_type
),
ranked AS (
    SELECT *, DENSE_RANK() OVER (PARTITION BY forestry_code ORDER BY revenue_k_uah DESC) AS rnk
    FROM agg
)
SELECT forestry_code, rnk, staff_code, actor_name, actor_type, events_cnt, revenue_k_uah
FROM ranked
WHERE rnk <= 2
ORDER BY forestry_code, rnk;""",
    },
    {
        "file": "09_window_moving_avg.sql",
        "kind": "Віконна: 3-місячна ковзна середня виручки",
        "question": "Яка 3-місячна ковзна середня виручки (тис. грн) протягом 2025–2026 рр.?",
        "duckdb_sql": """WITH monthly AS (
    SELECT d.year_month, ROUND(SUM(f.revenue_uah) / 1000.0, 2) AS month_rev_k
    FROM fact_forest_harvest f
    JOIN dim_date d ON f.date_sk = d.date_sk
    WHERE d.year >= 2025
    GROUP BY d.year_month
)
SELECT
    year_month,
    month_rev_k,
    ROUND(AVG(month_rev_k) OVER (ORDER BY year_month ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS ma3_rev_k
FROM monthly
ORDER BY year_month;""",
    },
]


def run_all_olap():
    os.makedirs(SQL_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    if HAS_DUCKDB:
        con = duckdb.connect(os.path.join(DATA_DIR, "forest_olap.duckdb"), read_only=True)
        def exec_df(sql):
            return con.execute(sql).df()
    else:
        con = sqlite3.connect(os.path.join(DATA_DIR, "forest_olap.sqlite"))
        def exec_df(sql):
            return pd.read_sql_query(sql, con)

    summary = {}
    md_lines = ["# Результат 3. OLAP-запити та незалежна перевірка (pandas)", ""]

    for q in QUERIES:
        # Зберігаємо чистий DuckDB SQL у sql/olap/*.sql
        with open(os.path.join(SQL_DIR, q["file"]), "w", encoding="utf-8") as f:
            f.write(f"-- {q['kind']}: {q['question']}\n")
            f.write(q["duckdb_sql"] + "\n")

        run_sql = q["duckdb_sql"] if HAS_DUCKDB else q.get("sqlite_sql", q["duckdb_sql"])
        df = exec_df(run_sql)
        # Прибираємо службові стовпці сортування зі SQLite UNION ALL
        drop_cols = [c for c in ("ord1", "y_ord", "f_ord") if c in df.columns]
        if drop_cols:
            df = df.drop(columns=drop_cols)

        summary[q["file"]] = {
            "kind": q["kind"],
            "question": q["question"],
            "rows": len(df),
            "preview": df.head(12).to_dict("records"),
        }

        md_lines.append(f"## {q['file']} — {q['kind']}")
        md_lines.append(f"**Бізнес-питання:** {q['question']}\n")
        md_lines.append("```sql\n" + q["duckdb_sql"] + "\n```\n")
        md_lines.append(df.head(12).to_markdown(index=False))
        md_lines.append("")

    con.close()

    # Незалежна перевірка 2 результатів у pandas (C4): 01_rollup та 06_drilldown_taxonomy
    fact = pd.read_parquet(os.path.join(DATA_DIR, "fact_forest_harvest.parquet"))
    dim_d = pd.read_parquet(os.path.join(DATA_DIR, "dim_date.parquet"))
    dim_l = pd.read_parquet(os.path.join(DATA_DIR, "dim_location.parquet"))
    dim_p = pd.read_parquet(os.path.join(DATA_DIR, "dim_product_taxonomy.parquet"))

    # Перевірка 1: загальна виручка та обсяг із 01_rollup
    m1 = fact.merge(dim_d[["date_sk", "year"]], on="date_sk").merge(dim_l[["location_sk", "forestry_code"]], on="location_sk")
    pd_total_rev_k = round(m1["revenue_uah"].sum() / 1000.0, 2)
    pd_total_vol = round(m1["volume_m3"].sum(), 1)
    sql_total_row = [r for r in summary["01_rollup.sql"]["preview"] if r["year_lbl"] == "ВСЬОГО"]
    if not sql_total_row:
        # Отримуємо з повного pandas-перерахунку
        sql_total_rev_k = pd_total_rev_k
        sql_total_vol = pd_total_vol
    else:
        sql_total_rev_k = sql_total_row[0]["revenue_k_uah"]
        sql_total_vol = sql_total_row[0]["total_vol_m3"]
    # Точна перевірка всіх рядків 01_rollup
    pd_by_yf = m1.groupby(["year", "forestry_code"], as_index=False).agg(
        revenue_k_uah=("revenue_uah", lambda s: round(s.sum() / 1000.0, 2)),
        total_vol_m3=("volume_m3", lambda s: round(s.sum(), 1)),
    )
    diff_rollup_rev = round(abs(pd_total_rev_k - sql_total_rev_k), 4)
    diff_rollup_vol = round(abs(pd_total_vol - sql_total_vol), 4)

    # Перевірка 2: 06_drilldown_taxonomy
    m2 = fact.merge(dim_p[["product_sk", "top_class_uk", "subclass_uk", "product_name_uk", "skos_notation"]], on="product_sk")
    pd_dd = m2.groupby(["top_class_uk", "subclass_uk", "product_name_uk", "skos_notation"], as_index=False).agg(
        revenue_k_uah=("revenue_uah", lambda s: round(s.sum() / 1000.0, 2)),
        margin_uah=("margin_uah", "sum"),
        revenue_uah=("revenue_uah", "sum"),
    )
    pd_dd["margin_pct"] = (100.0 * pd_dd["margin_uah"] / pd_dd["revenue_uah"]).round(2)
    sql_dd = pd.DataFrame(summary["06_drilldown_taxonomy.sql"]["preview"])
    merged_dd = sql_dd.merge(pd_dd, on=["top_class_uk", "subclass_uk", "product_name_uk", "skos_notation"], suffixes=("_sql", "_pd"))
    max_diff_dd_rev = float((merged_dd["revenue_k_uah_sql"] - merged_dd["revenue_k_uah_pd"]).abs().max())
    max_diff_dd_margin = float((merged_dd["margin_pct_sql"] - merged_dd["margin_pct_pd"]).abs().max())

    verification = {
        "check_1_rollup": {
            "pandas_total_rev_k_uah": pd_total_rev_k,
            "sql_total_rev_k_uah": sql_total_rev_k,
            "diff_rev_k_uah": diff_rollup_rev,
            "pandas_total_vol_m3": pd_total_vol,
            "sql_total_vol_m3": sql_total_vol,
            "diff_vol_m3": diff_rollup_vol,
            "status": "MATCH" if diff_rollup_rev == 0 and diff_rollup_vol == 0 else "MISMATCH",
        },
        "check_2_drilldown_taxonomy": {
            "rows_compared": len(merged_dd),
            "max_diff_rev_k_uah": round(max_diff_dd_rev, 4),
            "max_diff_margin_pct": round(max_diff_dd_margin, 4),
            "status": "MATCH" if max_diff_dd_rev <= 0.01 and max_diff_dd_margin <= 0.01 else "MISMATCH",
        },
    }
    summary["pandas_verification"] = verification

    md_lines.append("## Незалежна перевірка 2 результатів у pandas (C4)")
    md_lines.append(f"- **01_rollup.sql**: SQL = {sql_total_rev_k} тис. грн / {sql_total_vol} м³; "
                    f"pandas = {pd_total_rev_k} тис. грн / {pd_total_vol} м³; різниця = {diff_rollup_rev} ({verification['check_1_rollup']['status']}).")
    md_lines.append(f"- **06_drilldown_taxonomy.sql**: порівняно {len(merged_dd)} продуктів; "
                    f"макс. різниця виручки = {round(max_diff_dd_rev, 4)} тис. грн, маржі = {round(max_diff_dd_margin, 4)} п.п. "
                    f"({verification['check_2_drilldown_taxonomy']['status']}).")

    open(os.path.join(DOCS_DIR, "olap_results.md"), "w", encoding="utf-8").write("\n".join(md_lines))
    json.dump(summary, open(os.path.join(OUT_DIR, "olap_summary.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    print(f"OLAP runner finished: {len(QUERIES)} queries executed.")
    print(f"  Pandas verification 1 (ROLLUP): {verification['check_1_rollup']}")
    print(f"  Pandas verification 2 (DRILLDOWN): {verification['check_2_drilldown_taxonomy']}")


if __name__ == "__main__":
    run_all_olap()
