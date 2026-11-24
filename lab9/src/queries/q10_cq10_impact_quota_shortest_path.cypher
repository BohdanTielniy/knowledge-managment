// CQ10 (Аналіз впливу №2): Каскадний вплив перевищення квоти (глибина >= 3) + shortestPath(Forester, Threat).
// Частина A: Що зачепить порушення/зміна квоти (Quota <- Process -> Compartment -> Forestry + Permit + Forester).
MATCH (q:HarvestQuota)<-[r1:CONSTRAINED_BY]-(p:TimberHarvesting)-[r2:APPLIED_TO]->(c:Compartment)-[r3:PART_OF_FORESTRY]->(f:Forestry)
WHERE p.harvestVolumeM3 > q.limitValue
MATCH (p)-[r4:REQUIRES_PERMIT]->(pm:Permit),
      (fo:Forester)-[r5:SUPERVISES]->(c)
OPTIONAL MATCH (p)-[:FOLLOWED_BY]->(rf:Reforestation)
RETURN q.id AS quotaId,
       q.limitValue AS quotaLimitM3,
       p.id AS processId,
       p.harvestVolumeM3 AS plannedVolumeM3,
       round(p.harvestVolumeM3 - q.limitValue, 1) AS overrunM3,
       pm.number AS permitNumber,
       c.unitCode AS compartment,
       f.unitCode AS forestry,
       fo.staffCode AS supervisingForester,
       rf.id AS plannedReforestation,
       [r1.source, r2.source, r3.source, r4.source, r5.source] AS provenanceSources;

// Частина B: Найкоротший шлях (shortestPath) від базового лісника F-104 (Фомін О.В.) до кожної загрози в базі знань.
MATCH (fo:Forester {id: 'Forester_F104'}), (t:Threat)
MATCH path = shortestPath((fo)-[*1..6]-(t))
RETURN fo.name AS forester,
       t.id AS threatId,
       t.name AS threatName,
       length(path) AS hops,
       [n IN nodes(path) | coalesce(n.unitCode, n.id)] AS pathNodes,
       [r IN relationships(path) | type(r)] AS pathRels
ORDER BY hops ASC, threatId ASC;
