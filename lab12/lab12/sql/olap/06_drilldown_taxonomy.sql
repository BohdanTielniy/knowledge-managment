-- DRILL-DOWN по таксономії (клас -> підклас -> продукт IRI): Який внесок кожного рівня ієрархії таксономії (клас -> підклас -> продукт) у загальну виручку та маржу?
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
