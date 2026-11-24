-- DICE (2025-2026, LS-01/LS-03, Деревинні): Які обсяги та середня ціна деревини у 2025–2026 рр. у гірських лісництвах LS-01 та LS-03?
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
