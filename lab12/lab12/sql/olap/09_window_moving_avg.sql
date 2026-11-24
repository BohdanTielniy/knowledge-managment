-- Віконна: 3-місячна ковзна середня виручки: Яка 3-місячна ковзна середня виручки (тис. грн) протягом 2025–2026 рр.?
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
