-- Віконна: накопичувальна виручка (YTD): Як зростає накопичувальна виручка (YTD, тис. грн) помісячно у 2025 році?
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
