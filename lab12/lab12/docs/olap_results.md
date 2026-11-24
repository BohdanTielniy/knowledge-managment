# Результат 3. OLAP-запити та незалежна перевірка (pandas)

## 01_rollup.sql — ROLLUP
**Бізнес-питання:** Яка динаміка виручки (тис. грн) та обсягу деревини (м³) з проміжними підсумками за роками та лісництвами?

```sql
SELECT
    COALESCE(CAST(d.year AS VARCHAR), 'ВСЬОГО') AS year_lbl,
    COALESCE(l.forestry_code, 'Усі лісництва') AS forestry_code,
    COUNT(*) AS events_cnt,
    ROUND(SUM(f.volume_m3), 1) AS total_vol_m3,
    ROUND(SUM(f.revenue_uah) / 1000.0, 2) AS revenue_k_uah
FROM fact_forest_harvest f
JOIN dim_date d ON f.date_sk = d.date_sk
JOIN dim_location l ON f.location_sk = l.location_sk
GROUP BY ROLLUP (d.year, l.forestry_code)
ORDER BY d.year NULLS LAST, l.forestry_code NULLS LAST;
```

|   year_lbl | forestry_code   |   events_cnt |   total_vol_m3 |   revenue_k_uah |
|-----------:|:----------------|-------------:|---------------:|----------------:|
|       2024 | LS-01           |          206 |         3516   |        15601.5  |
|       2024 | LS-02           |          141 |         2372.3 |        10601.3  |
|       2024 | LS-03           |          130 |         2356   |        10188.1  |
|       2024 | LS-04           |           52 |          608.3 |         2868.42 |
|       2024 | Усі лісництва   |          529 |         8852.7 |        39259.3  |
|       2025 | LS-01           |          196 |         2947.1 |        13226.6  |
|       2025 | LS-02           |          127 |         1913.8 |         9957.45 |
|       2025 | LS-03           |          136 |         2197.5 |        10055.1  |
|       2025 | LS-04           |           58 |          671.4 |         3113.21 |
|       2025 | Усі лісництва   |          517 |         7729.8 |        36352.4  |
|       2026 | LS-01           |          158 |         2819.4 |        12392.4  |
|       2026 | LS-02           |          116 |         1947   |         8915.99 |

## 02_cube_grouping_sets.sql — GROUPING SETS / CUBE
**Бізнес-питання:** Як розподіляється виручка та рентабельність за класом таксономії та статусом FSC-сертифікації (усі комбінації)?

```sql
SELECT
    COALESCE(p.top_class_uk, 'Усі класи') AS top_class_uk,
    COALESCE(CASE WHEN l.fsc_certified THEN 'FSC-так' ELSE 'FSC-ні' END, 'Усі статуси') AS fsc_status,
    COUNT(*) AS events_cnt,
    ROUND(SUM(f.revenue_uah) / 1000.0, 2) AS revenue_k_uah,
    ROUND(100.0 * SUM(f.margin_uah) / NULLIF(SUM(f.revenue_uah), 0), 2) AS margin_pct
FROM fact_forest_harvest f
JOIN dim_product_taxonomy p ON f.product_sk = p.product_sk
JOIN dim_location l ON f.location_sk = l.location_sk
GROUP BY CUBE (p.top_class_uk, CASE WHEN l.fsc_certified THEN 'FSC-так' ELSE 'FSC-ні' END)
ORDER BY top_class_uk, fsc_status;
```

| top_class_uk         | fsc_status   |   events_cnt |   revenue_k_uah |   margin_pct |
|:---------------------|:-------------|-------------:|----------------:|-------------:|
| Деревинні продукти   | FSC-ні       |          242 |        18432.8  |        36.24 |
| Деревинні продукти   | FSC-так      |          944 |        73212.5  |        36.12 |
| Деревинні продукти   | Усі статуси  |         1186 |        91645.3  |        36.14 |
| Недеревинні продукти | FSC-ні       |           56 |         2925.19 |        50.22 |
| Недеревинні продукти | FSC-так      |          258 |        14656.2  |        51.04 |
| Недеревинні продукти | Усі статуси  |          314 |        17581.4  |        50.9  |
| Усі класи            | FSC-ні       |          298 |        21358    |        38.15 |
| Усі класи            | FSC-так      |         1202 |        87868.7  |        38.61 |
| Усі класи            | Усі статуси  |         1500 |       109227    |        38.52 |

## 03_slice.sql — SLICE (year = 2025)
**Бізнес-питання:** Яка структура виручки та обсягів у 2025 році за підкласами продуктів?

```sql
SELECT
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
ORDER BY revenue_k_uah DESC;
```

| subclass_uk       |   events_cnt |   total_vol_m3 |   total_mass_kg |   revenue_k_uah |
|:------------------|-------------:|---------------:|----------------:|----------------:|
| Хвойна деревина   |          236 |         4699.4 |             0   |        17114.8  |
| Листяна деревина  |          112 |         2172   |             0   |        11052.9  |
| Гриби             |           48 |            0   |          9073   |         3667.73 |
| Ягоди             |           59 |            0   |          9548.7 |         2311.82 |
| Паливна деревина  |           46 |          858.4 |             0   |         1332.98 |
| Лікарські рослини |           16 |            0   |          2792.3 |          872.17 |

## 04_dice.sql — DICE (2025-2026, LS-01/LS-03, Деревинні)
**Бізнес-питання:** Які обсяги та середня ціна деревини у 2025–2026 рр. у гірських лісництвах LS-01 та LS-03?

```sql
SELECT
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
ORDER BY d.year, l.forestry_code, total_vol_m3 DESC;
```

|   year | forestry_code   | subclass_uk      |   total_vol_m3 |   weighted_price_uah_m3 |   avg_ndvi |
|-------:|:----------------|:-----------------|---------------:|------------------------:|-----------:|
|   2025 | LS-01           | Хвойна деревина  |         2000.4 |                 3629.19 |      0.718 |
|   2025 | LS-01           | Листяна деревина |          614.4 |                 5139.54 |      0.749 |
|   2025 | LS-01           | Паливна деревина |          332.2 |                 1542.17 |      0.72  |
|   2025 | LS-03           | Хвойна деревина  |         1228.7 |                 3600.68 |      0.672 |
|   2025 | LS-03           | Листяна деревина |          755.3 |                 5102.63 |      0.659 |
|   2025 | LS-03           | Паливна деревина |          213.5 |                 1571.15 |      0.714 |
|   2026 | LS-01           | Хвойна деревина  |         1807.1 |                 3648.77 |      0.725 |
|   2026 | LS-01           | Листяна деревина |          697.7 |                 4952.68 |      0.721 |
|   2026 | LS-01           | Паливна деревина |          314.5 |                 1542.05 |      0.705 |
|   2026 | LS-03           | Хвойна деревина  |          916.3 |                 3662.99 |      0.686 |
|   2026 | LS-03           | Листяна деревина |          704.7 |                 5023.55 |      0.64  |
|   2026 | LS-03           | Паливна деревина |          112.1 |                 1453.89 |      0.659 |

## 05_pivot.sql — PIVOT (квартали по лісництвах)
**Бізнес-питання:** Як розподіляється виручка (тис. грн) кожного лісництва по кварталах Q1–Q4 (зведена матриця)?

```sql
SELECT
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
ORDER BY total_k_uah DESC;
```

| forestry_code   | forestry_name            |   Q1_k_uah |   Q2_k_uah |   Q3_k_uah |   Q4_k_uah |   total_k_uah |
|:----------------|:-------------------------|-----------:|-----------:|-----------:|-----------:|--------------:|
| LS-01           | Лісництво «Карпатське»   |   11045    |   12063.8  |    9098.11 |    9013.53 |       41220.5 |
| LS-02           | Лісництво «Бескидське»   |    6907.61 |    7960.63 |    7723.8  |    6882.73 |       29474.8 |
| LS-03           | Лісництво «Верховинське» |    7072.54 |    8114.64 |    6019.46 |    7051.38 |       28258   |
| LS-04           | Лісництво «Дністровське» |    2148.14 |    2915.34 |    3326.22 |    1883.74 |       10273.4 |

## 06_drilldown_taxonomy.sql — DRILL-DOWN по таксономії (клас -> підклас -> продукт IRI)
**Бізнес-питання:** Який внесок кожного рівня ієрархії таксономії (клас -> підклас -> продукт) у загальну виручку та маржу?

```sql
SELECT
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
ORDER BY p.top_class_uk, revenue_k_uah DESC;
```

| top_class_uk         | subclass_uk       | product_name_uk      | skos_notation   |   events_cnt |   revenue_k_uah |   share_total_pct |   margin_pct |
|:---------------------|:------------------|:---------------------|:----------------|-------------:|----------------:|------------------:|-------------:|
| Деревинні продукти   | Листяна деревина  | Деревина дуба        | FP-TIM-BRD-02   |          146 |        18782.3  |             17.2  |        36.29 |
| Деревинні продукти   | Хвойна деревина   | Деревина ялини       | FP-TIM-CON-01   |          238 |        17604.5  |             16.12 |        35.61 |
| Деревинні продукти   | Листяна деревина  | Деревина бука        | FP-TIM-BRD-01   |          198 |        16930.9  |             15.5  |        35.6  |
| Деревинні продукти   | Хвойна деревина   | Деревина сосни       | FP-TIM-CON-03   |          183 |        13009.2  |             11.91 |        36.7  |
| Деревинні продукти   | Хвойна деревина   | Деревина ялиці       | FP-TIM-CON-02   |          166 |        11686.6  |             10.7  |        36.85 |
| Деревинні продукти   | Хвойна деревина   | Деревина модрини     | FP-TIM-CON-04   |          109 |         9247.23 |              8.47 |        36.18 |
| Деревинні продукти   | Паливна деревина  | Дрова твердолистяних | FP-TIM-FUL-01   |          146 |         4384.62 |              4.01 |        36.14 |
| Недеревинні продукти | Гриби             | Білі гриби           | FP-NTF-MSH-01   |          102 |         8063.83 |              7.38 |        51.17 |
| Недеревинні продукти | Ягоди             | Чорниця              | FP-NTF-BER-01   |           88 |         3427.47 |              3.14 |        50.35 |
| Недеревинні продукти | Ягоди             | Малина лісова        | FP-NTF-BER-02   |           71 |         3211.05 |              2.94 |        50.76 |
| Недеревинні продукти | Лікарські рослини | Звіробій             | FP-NTF-HRB-01   |           53 |         2879.02 |              2.64 |        50.95 |

## 07_window_cumulative.sql — Віконна: накопичувальна виручка (YTD)
**Бізнес-питання:** Як зростає накопичувальна виручка (YTD, тис. грн) помісячно у 2025 році?

```sql
WITH monthly AS (
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
ORDER BY year_month;
```

| year_month   |   month_rev_k |   ytd_rev_k |
|:-------------|--------------:|------------:|
| 2025-01      |       3396.45 |     3396.45 |
| 2025-02      |       2691.53 |     6087.98 |
| 2025-03      |       2862.87 |     8950.85 |
| 2025-04      |       3214.26 |    12165.1  |
| 2025-05      |       3429.32 |    15594.4  |
| 2025-06      |       2431.09 |    18025.5  |
| 2025-07      |       2400.74 |    20426.3  |
| 2025-08      |       3626.82 |    24053.1  |
| 2025-09      |       3135.43 |    27188.5  |
| 2025-10      |       3582.81 |    30771.3  |
| 2025-11      |       2980.21 |    33751.5  |
| 2025-12      |       2600.84 |    36352.4  |

## 08_window_rank.sql — Віконна: DENSE_RANK виконавців у лісництвах
**Бізнес-питання:** Хто з лісників і бригад входить у топ-2 за виручкою в кожному лісництві?

```sql
WITH agg AS (
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
ORDER BY forestry_code, rnk;
```

| forestry_code   |   rnk | staff_code   | actor_name               | actor_type     |   events_cnt |   revenue_k_uah |
|:----------------|------:|:-------------|:-------------------------|:---------------|-------------:|----------------:|
| LS-01           |     1 | BR-01        | Бригада лісозаготівлі №1 | HarvestBrigade |          172 |        19383.2  |
| LS-01           |     2 | F-101        | Лісник F-101             | Forester       |          198 |        11472.3  |
| LS-02           |     1 | BR-02        | Бригада лісозаготівлі №2 | HarvestBrigade |          132 |        14883.1  |
| LS-02           |     2 | F-201        | Лісник F-201             | Forester       |          134 |         7742.88 |
| LS-03           |     1 | BR-03        | Бригада лісозаготівлі №3 | HarvestBrigade |          123 |        14264.9  |
| LS-03           |     2 | F-302        | Лісник F-302             | Forester       |          136 |         7458.67 |
| LS-04           |     1 | F-401        | Лісник F-401             | Forester       |          183 |        10273.4  |

## 09_window_moving_avg.sql — Віконна: 3-місячна ковзна середня виручки
**Бізнес-питання:** Яка 3-місячна ковзна середня виручки (тис. грн) протягом 2025–2026 рр.?

```sql
WITH monthly AS (
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
ORDER BY year_month;
```

| year_month   |   month_rev_k |   ma3_rev_k |
|:-------------|--------------:|------------:|
| 2025-01      |       3396.45 |     3396.45 |
| 2025-02      |       2691.53 |     3043.99 |
| 2025-03      |       2862.87 |     2983.62 |
| 2025-04      |       3214.26 |     2922.89 |
| 2025-05      |       3429.32 |     3168.82 |
| 2025-06      |       2431.09 |     3024.89 |
| 2025-07      |       2400.74 |     2753.72 |
| 2025-08      |       3626.82 |     2819.55 |
| 2025-09      |       3135.43 |     3054.33 |
| 2025-10      |       3582.81 |     3448.35 |
| 2025-11      |       2980.21 |     3232.82 |
| 2025-12      |       2600.84 |     3054.62 |

## Незалежна перевірка 2 результатів у pandas (C4)
- **01_rollup.sql**: SQL = 109226.69 тис. грн / 23952.0 м³; pandas = 109226.69 тис. грн / 23952.0 м³; різниця = 0.0 (MATCH).
- **06_drilldown_taxonomy.sql**: порівняно 11 продуктів; макс. різниця виручки = 0.0 тис. грн, маржі = 0.0 п.п. (MATCH).