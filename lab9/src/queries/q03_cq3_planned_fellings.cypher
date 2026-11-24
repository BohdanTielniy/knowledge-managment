// CQ3: Які рубки заплановані, який обсяг, квиток, виконавець і чи перевищено квоту?
// Конструкції: MATCH за міткою надкласу :TimberHarvesting, обчислюване булеве поле, WITH, агрегація.
MATCH (p:TimberHarvesting)-[:APPLIED_TO]->(c:Compartment),
      (p)-[rp:REQUIRES_PERMIT]->(pm:Permit),
      (p)-[:CONSTRAINED_BY]->(q:HarvestQuota),
      (p)-[:PERFORMED_BY]->(a:Actor)
WITH p, c, pm, q, a, rp,
     (p.harvestVolumeM3 > q.limitValue) AS exceedsQuota,
     (c.annualIncrementM3 IS NOT NULL AND p.harvestVolumeM3 > c.annualIncrementM3) AS exceedsIncrement
RETURN p.id AS processId,
       CASE WHEN p:SanitaryFelling THEN 'SanitaryFelling' ELSE 'MainFelling' END AS fellingType,
       c.unitCode AS compartment,
       p.harvestVolumeM3 AS volumeM3,
       q.limitValue AS quotaM3,
       exceedsQuota,
       exceedsIncrement,
       pm.number AS permitNumber,
       a.name AS actor,
       rp.source AS permitSource
ORDER BY volumeM3 DESC, processId ASC;
