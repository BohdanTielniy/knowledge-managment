// CQ4: Які виділи — стиглі хвойні (вік >= 81 р.) і які сумарні показники по лісництвах?
// Конструкції: MATCH із підміткою :ConiferousSpecies, WHERE, WITH, агрегації (count, sum, avg, collect).
MATCH (c:Compartment)-[hs:HAS_DOMINANT_SPECIES]->(s:ConiferousSpecies),
      (c)-[:PART_OF_FORESTRY]->(f:Forestry)
WHERE c.standAgeYears >= 81
WITH f,
     count(c) AS matureCount,
     round(sum(c.timberStockM3), 1) AS totalStockM3,
     round(sum(c.areaHectares), 1) AS totalAreaHa,
     round(avg(c.standAgeYears), 1) AS avgAgeYears,
     round(min(hs.confidence), 2) AS minConfidence,
     collect(c.unitCode) AS compartments
RETURN f.unitCode AS forestryCode,
       f.name AS forestryName,
       matureCount,
       totalAreaHa,
       totalStockM3,
       avgAgeYears,
       minConfidence,
       compartments
ORDER BY totalStockM3 DESC;
