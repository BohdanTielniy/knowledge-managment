// ЛР 9, Результат 4 (Крок 3 / C3): PROFILE для 2 запитів та оптимізація одного з них (до/після).

// ============================================================================
// ЗАПИТ 1 (PROFILE): Запит CQ8 (виділи з NDVI < 0.65) — використовує індекс compartment_ndvi
// ============================================================================
PROFILE
MATCH (c:Compartment)-[:PART_OF_FORESTRY]->(f:Forestry)
WHERE c.ndviValue < 0.65
OPTIONAL MATCH (c)-[:AFFECTED_BY]->(t:Threat)
RETURN c.unitCode AS compartment, f.unitCode AS forestry, c.ndviValue AS ndvi, collect(t.name) AS threats
ORDER BY ndvi ASC;

// ============================================================================
// ЗАПИТ 2 (ДО ОПТИМІЗАЦІЇ — PROFILE):
// Пошук рубок з великим обсягом (>= 200 м³) та їхніх лісництв.
// Неоптимальний варіант: сканування без мітки + фільтр на пізньому етапі (AllNodesScan / NodeByLabelScan без індексу).
// ============================================================================
PROFILE
MATCH (p)-[:APPLIED_TO]->(c)-[:PART_OF_FORESTRY]->(f)
WHERE 'TimberHarvesting' IN labels(p)
  AND p.harvestVolumeM3 >= 200.0
  AND c.standAgeYears >= 81
RETURN p.id AS processId, c.unitCode AS compartment, f.unitCode AS forestry, p.harvestVolumeM3 AS volumeM3
ORDER BY volumeM3 DESC;

// ============================================================================
// ОПТИМІЗАЦІЯ:
// 1) Додаємо індекс на Process(harvestVolumeM3) (а також вже є індекс compartment_age на Compartment(standAgeYears)).
// 2) Переписуємо запит: вказуємо конкретні мітки (:TimberHarvesting, :Compartment, :Forestry)
//    і фільтруємо через індексовану властивість c.standAgeYears >= 81 першим кроком (NodeIndexSeek).
// ============================================================================
CREATE INDEX process_harvest_volume IF NOT EXISTS FOR (p:Process) ON (p.harvestVolumeM3);
SHOW INDEXES;

// ============================================================================
// ЗАПИТ 2 (ПІСЛЯ ОПТИМІЗАЦІЇ — PROFILE):
// Використовує NodeIndexSeek по compartment_age / process_harvest_volume замість AllNodesScan.
// ============================================================================
PROFILE
MATCH (c:Compartment)
WHERE c.standAgeYears >= 81
MATCH (p:TimberHarvesting)-[:APPLIED_TO]->(c)
WHERE p.harvestVolumeM3 >= 200.0
MATCH (c)-[:PART_OF_FORESTRY]->(f:Forestry)
RETURN p.id AS processId, c.unitCode AS compartment, f.unitCode AS forestry, p.harvestVolumeM3 AS volumeM3
ORDER BY volumeM3 DESC;
