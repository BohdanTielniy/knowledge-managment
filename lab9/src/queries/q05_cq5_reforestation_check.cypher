// CQ5: Яке лісовідновлення закріплене за ділянками після рубок (і які рубки не мають лісовідновлення)?
// Конструкції: OPTIONAL MATCH, перевірка IS NULL, WITH, умовний статус CASE.
MATCH (h:TimberHarvesting)-[:APPLIED_TO]->(c:Compartment)
OPTIONAL MATCH (h)-[fb:FOLLOWED_BY]->(r:Reforestation)
WITH h, c, r, fb
RETURN h.id AS harvestingId,
       c.unitCode AS compartment,
       CASE WHEN r IS NULL THEN 'ВІДСУТНЄ (потребує планування)' ELSE 'Заплановано' END AS status,
       r.id AS reforestationId,
       r.plantedSeedlingsCount AS seedlings,
       fb.validFrom AS reforestationValidFrom
ORDER BY (r IS NULL) DESC, harvestingId ASC;
