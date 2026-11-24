-- GROUPING SETS / CUBE: Як розподіляється виручка та рентабельність за класом таксономії та статусом FSC-сертифікації (усі комбінації)?
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
