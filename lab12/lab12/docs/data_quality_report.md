# Звіт якості даних (Результат 2 — ELT)
- **Версія набору даних**: `1.0.0` (`seed=42`, рушій завантаження: `sqlite3`)
- **Рядків у `fact_forest_harvest`**: 1500 (вимога ≥ 1000)

| Код перевірки | Опис | Значення | Статус |
|---|---|---:|---|
| `DQ1_fact_row_count_ge_1000` | Кількість рядків факту >= 1000 | 1500 | PASS |
| `DQ2_no_orphan_keys` | Відсутність «сиріт» за всіма 5 FK | 0 | PASS |
| `DQ3_not_null_critical` | Відсутність NULL у ключах і мірах | 0 | PASS |
| `DQ4_positive_revenue_and_nonneg_qty` | Діапазон: revenue_uah > 0, volume_m3 >= 0, mass_kg >= 0 | 0 | PASS |
| `DQ5_ndvi_range_0_1` | Діапазон екологічної метрики: 0 <= ndvi_score <= 1 | 0 | PASS |
| `DQ6_unique_fact_id_and_iri` | Унікальність fact_id та product_iri | 0 | PASS |
| `DQ7_margin_arithmetic` | Узгодженість формули |margin_uah - (revenue_uah - cost_uah)| < 0.02 | 0 | PASS |

## Parquet-файли (`data/*.parquet`)
- `dim_date.parquet`: 1035 рядків, 10 стовпців, SHA-256=`a390e26c667b1a75`
- `dim_product_taxonomy.parquet`: 11 рядків, 12 стовпців, SHA-256=`b33516ea4efe8220`
- `dim_location.parquet`: 18 рядків, 14 стовпців, SHA-256=`2a732c17be895b46`
- `dim_actor.parquet`: 10 рядків, 10 стовпців, SHA-256=`398f0a55343e3bb2`
- `dim_permit.parquet`: 9 рядків, 6 стовпців, SHA-256=`9da1604c95f1d865`
- `fact_forest_harvest.parquet`: 1500 рядків, 18 стовпців, SHA-256=`83c127ce36cddbf0`