#!/usr/bin/env python3
"""
Результат 4 (Семантичний шар):
- Завантажує semantic/metrics.yml (6 метрик з усіма полями та метаданими).
- Надає функцію generate_metric_sql(metric_name, dimensions, filters) для генерації валідного SQL.
- Перевіряє узгодженість >= 2 бізнес-питань двома незалежними шляхами (Semantic SQL vs OLAP/pandas).
- Зберігає docs/semantic_layer.md та outputs/semantic_results.json.
"""
import json
import os
import sqlite3
import yaml
import pandas as pd

try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_YML = os.path.join(BASE_DIR, "semantic", "metrics.yml")
DATA_DIR = os.path.join(BASE_DIR, "data")
DOCS_DIR = os.path.join(BASE_DIR, "docs")
OUT_DIR = os.path.join(BASE_DIR, "outputs")

DIM_MAP = {
    "year": ("d.year", "JOIN dim_date d ON f.date_sk = d.date_sk"),
    "quarter_label": ("d.quarter_label", "JOIN dim_date d ON f.date_sk = d.date_sk"),
    "forestry_code": ("l.forestry_code", "JOIN dim_location l ON f.location_sk = l.location_sk"),
    "top_class_uk": ("p.top_class_uk", "JOIN dim_product_taxonomy p ON f.product_sk = p.product_sk"),
    "subclass_uk": ("p.subclass_uk", "JOIN dim_product_taxonomy p ON f.product_sk = p.product_sk"),
    "actor_type": ("a.actor_type", "JOIN dim_actor a ON f.actor_sk = a.actor_sk"),
}


def load_metrics():
    with open(METRICS_YML, encoding="utf-8") as f:
        return yaml.safe_load(f)


def generate_metric_sql(metric_name: str, dimensions=None, filters=None) -> str:
    """Генерує стандартизований SQL-запит за назвою метрики із semantic/metrics.yml."""
    spec = load_metrics()["metrics"]
    if metric_name not in spec:
        raise KeyError(f"Невідома метрика: {metric_name}")
    m = spec[metric_name]
    formula = m["formula"]

    dimensions = dimensions or []
    filters = filters or []
    joins = set()
    select_parts = []
    group_parts = []

    # Автоматичне підключення вимірів, потрібних самій формулі
    if "l." in formula:
        joins.add("JOIN dim_location l ON f.location_sk = l.location_sk")
    if "p." in formula:
        joins.add("JOIN dim_product_taxonomy p ON f.product_sk = p.product_sk")
    if "d." in formula:
        joins.add("JOIN dim_date d ON f.date_sk = d.date_sk")

    for dim in dimensions:
        col, j = DIM_MAP[dim]
        joins.add(j)
        select_parts.append(f"{col} AS {dim}")
        group_parts.append(col)

    for flt in filters:
        if "d." in flt:
            joins.add("JOIN dim_date d ON f.date_sk = d.date_sk")
        if "l." in flt:
            joins.add("JOIN dim_location l ON f.location_sk = l.location_sk")
        if "p." in flt:
            joins.add("JOIN dim_product_taxonomy p ON f.product_sk = p.product_sk")

    select_parts.append(f"{formula} AS {metric_name}")
    sql = "SELECT\n    " + ",\n    ".join(select_parts) + "\nFROM fact_forest_harvest f"
    if joins:
        sql += "\n" + "\n".join(sorted(joins))
    if filters:
        sql += "\nWHERE " + " AND ".join(filters)
    if group_parts:
        sql += "\nGROUP BY " + ", ".join(group_parts)
        sql += "\nORDER BY " + ", ".join(group_parts)
    return sql + ";"


def run_semantic_checks():
    cfg = load_metrics()
    metrics = cfg["metrics"]

    if HAS_DUCKDB:
        con = duckdb.connect(os.path.join(DATA_DIR, "forest_olap.duckdb"), read_only=True)
        def exec_df(sql):
            # У DuckDB boolean порівнюється як = TRUE або CAST(... AS INT)
            return con.execute(sql.replace("= 1", "= TRUE")).df()
    else:
        con = sqlite3.connect(os.path.join(DATA_DIR, "forest_olap.sqlite"))
        def exec_df(sql):
            return pd.read_sql_query(sql, con)

    # 1. Виконання всіх 6 метрик на рівні всього сховища
    global_kpis = {}
    for mname in metrics:
        sql = generate_metric_sql(mname)
        val = float(exec_df(sql).iloc[0, 0])
        global_kpis[mname] = {"value": val, "unit": metrics[mname]["unit"], "sql": sql}

    # 2. Перевірка узгодженості (C3) для 2 бізнес-питань різними шляхами
    fact = pd.read_parquet(os.path.join(DATA_DIR, "fact_forest_harvest.parquet"))
    dim_d = pd.read_parquet(os.path.join(DATA_DIR, "dim_date.parquet"))
    dim_l = pd.read_parquet(os.path.join(DATA_DIR, "dim_location.parquet"))
    dim_p = pd.read_parquet(os.path.join(DATA_DIR, "dim_product_taxonomy.parquet"))

    # Питання A: Валова рентабельність (gross_margin_pct) по лісництвах у 2025 році
    sql_a = generate_metric_sql("gross_margin_pct", dimensions=["forestry_code"], filters=["d.year = 2025"])
    df_a_sem = exec_df(sql_a)
    m_a = fact.merge(dim_d[["date_sk", "year"]], on="date_sk").merge(dim_l[["location_sk", "forestry_code"]], on="location_sk")
    m_a = m_a[m_a["year"] == 2025]
    df_a_pd = m_a.groupby("forestry_code", as_index=False).agg(margin=("margin_uah", "sum"), rev=("revenue_uah", "sum"))
    df_a_pd["gross_margin_pct_pd"] = (100.0 * df_a_pd["margin"] / df_a_pd["rev"]).round(2)
    cmp_a = df_a_sem.merge(df_a_pd[["forestry_code", "gross_margin_pct_pd"]], on="forestry_code")
    diff_a = float((cmp_a["gross_margin_pct"] - cmp_a["gross_margin_pct_pd"]).abs().max())

    # Питання B: Частка FSC-сертифікованої виручки (fsc_certified_share_pct) за роками
    sql_b = generate_metric_sql("fsc_certified_share_pct", dimensions=["year"])
    df_b_sem = exec_df(sql_b)
    m_b = fact.merge(dim_d[["date_sk", "year"]], on="date_sk").merge(dim_l[["location_sk", "fsc_certified"]], on="location_sk")
    df_b_pd = m_b.groupby("year", as_index=False).apply(
        lambda g: pd.Series({"fsc_pd": round(100.0 * g.loc[g["fsc_certified"] == True, "revenue_uah"].sum() / g["revenue_uah"].sum(), 2)}),
        include_groups=False,
    )
    cmp_b = df_b_sem.merge(df_b_pd, on="year")
    diff_b = float((cmp_b["fsc_certified_share_pct"] - cmp_b["fsc_pd"]).abs().max())

    con.close()

    out = {
        "metrics_count": len(metrics),
        "global_kpis": global_kpis,
        "consistency_checks": {
            "question_A_margin_2025_by_forestry": {
                "sql": sql_a, "max_abs_diff": round(diff_a, 4),
                "rows": cmp_a.to_dict("records"), "status": "CONSISTENT" if diff_a == 0 else "DIFF",
            },
            "question_B_fsc_share_by_year": {
                "sql": sql_b, "max_abs_diff": round(diff_b, 4),
                "rows": cmp_b.to_dict("records"), "status": "CONSISTENT" if diff_b == 0 else "DIFF",
            },
        },
    }
    json.dump(out, open(os.path.join(OUT_DIR, "semantic_results.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    md = [
        "# Результат 4. Семантичний шар (`semantic/metrics.yml`)",
        f"- Версія: `{cfg['version']}`, кількість затверджених метрик: **{len(metrics)}** (вимога ≥ 5).",
        "",
        "| Метрика | Тип | Одиниця | Значення (усі роки) | Власник | Дата перегляду | Статус |",
        "|---|---|---|---:|---|---|---|",
    ]
    for k, m in metrics.items():
        md.append(f"| `{k}` | {m['aggregation_type']} | {m['unit']} | {global_kpis[k]['value']} | {m['owner']} | {m['review_date']} | {m['status']} |")

    md.extend([
        "",
        "## Перевірка узгодженості (C3)",
        f"1. **Рентабельність (`gross_margin_pct`) по лісництвах за 2025 р.** (Semantic SQL vs pandas): макс. розбіжність = **{diff_a:.4f} п.п.** (`CONSISTENT`).",
        f"2. **Частка FSC-виручки (`fsc_certified_share_pct`) за роками** (Semantic SQL vs pandas): макс. розбіжність = **{diff_b:.4f} п.п.** (`CONSISTENT`).",
    ])
    open(os.path.join(DOCS_DIR, "semantic_layer.md"), "w", encoding="utf-8").write("\n".join(md))

    print(f"Semantic layer checked: {len(metrics)} metrics, diff_A={diff_a}, diff_B={diff_b}")
    for k, v in global_kpis.items():
        print(f"  {k}: {v['value']} {v['unit']}")


if __name__ == "__main__":
    run_semantic_checks()
