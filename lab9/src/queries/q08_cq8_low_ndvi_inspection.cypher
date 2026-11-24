// CQ8: Які ділянки мають NDVI < 0.65 (першочергове обстеження), включно з раннім попередженням без зафіксованої загрози?
// Конструкції: індексована фільтрація WHERE (compartment_ndvi), OPTIONAL MATCH, агрегація, CASE-класифікація ризику.
MATCH (c:Compartment)-[:PART_OF_FORESTRY]->(f:Forestry)
WHERE c.ndviValue < 0.65
OPTIONAL MATCH (c)-[:AFFECTED_BY]->(t:Threat)
WITH c, f, collect(DISTINCT t.name) AS threats
RETURN c.unitCode AS compartment,
       f.unitCode AS forestry,
       c.ndviValue AS ndvi,
       c.damagedTreesShare AS damagedPct,
       CASE
         WHEN size(threats) = 0 THEN 'Раннє попередження (загрозу ще не ідентифіковано)'
         ELSE 'Підтверджена загроза'
       END AS inspectionPriority,
       threats
ORDER BY ndvi ASC, compartment ASC;
