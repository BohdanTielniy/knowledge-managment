-- PIVOT (квартали по лісництвах): Як розподіляється виручка (тис. грн) кожного лісництва по кварталах Q1–Q4 (зведена матриця)?
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
