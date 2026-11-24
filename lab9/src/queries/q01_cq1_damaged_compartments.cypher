// CQ1: Які виділи уражені (>10 %) і якою загрозою?
// Конструкції: MATCH (багатокроковий шаблон), WHERE (числовий поріг), ORDER BY, походження зв'язку.
MATCH (c:Compartment)-[:PART_OF_FORESTRY]->(f:Forestry),
      (c)-[:HAS_DOMINANT_SPECIES]->(s:TreeSpecies),
      (c)-[r:AFFECTED_BY]->(t:Threat)
WHERE c.damagedTreesShare > 10.0
RETURN c.unitCode AS compartment,
       f.unitCode AS forestry,
       s.name AS dominantSpecies,
       c.damagedTreesShare AS damagedPct,
       t.name AS threat,
       r.source AS source,
       r.confidence AS confidence
ORDER BY damagedPct DESC, compartment ASC;
