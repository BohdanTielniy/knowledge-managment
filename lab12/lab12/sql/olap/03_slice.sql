-- SLICE (year = 2025): Яка структура виручки та обсягів у 2025 році за підкласами продуктів?
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
