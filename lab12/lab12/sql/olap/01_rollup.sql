-- ROLLUP: Яка динаміка виручки (тис. грн) та обсягу деревини (м³) з проміжними підсумками за роками та лісництвами?
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
