// CQ6: Які лісники відповідають за виділи із загрозами або залучені до пожежного патрулювання?
// Конструкції: OPTIONAL MATCH (два незалежні контури відповідальності), WITH, агрегація collect(DISTINCT ...).
MATCH (a:Forester)
OPTIONAL MATCH (a)-[s:SUPERVISES]->(c:Compartment)-[:AFFECTED_BY]->(t:Threat)
WITH a,
     collect(DISTINCT CASE WHEN c IS NOT NULL THEN c.unitCode + ' (' + t.name + ')' END) AS threatCompartments,
     collect(DISTINCT s.source) AS supervisionSources
OPTIONAL MATCH (o:MeteoObservation)-[:TRIGGERS]->(fp:FirePreventionMeasure)-[:PERFORMED_BY]->(a)
WITH a, threatCompartments, supervisionSources,
     collect(DISTINCT CASE WHEN fp IS NOT NULL THEN fp.id + ' [' + toString(o.observationDate) + ']' END) AS firePatrols
WHERE size(threatCompartments) > 0 OR size(firePatrols) > 0
RETURN a.staffCode AS staffCode,
       a.name AS forester,
       size(threatCompartments) AS threatCount,
       threatCompartments,
       size(firePatrols) AS patrolCount,
       firePatrols
ORDER BY threatCount DESC, patrolCount DESC, staffCode ASC;
