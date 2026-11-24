-- Віконна: DENSE_RANK виконавців у лісництвах: Хто з лісників і бригад входить у топ-2 за виручкою в кожному лісництві?
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
