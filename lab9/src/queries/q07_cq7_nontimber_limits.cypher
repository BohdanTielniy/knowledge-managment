// CQ7: Які виділи дають недеревну продукцію і які ліміти збору діють для кожного продукту?
// Конструкції: MATCH із підмітками :NonTimberProduct і :NonTimberCollectionLimit, WITH, агрегації count/collect/avg.
MATCH (c:Compartment)-[yp:YIELDS_PRODUCT]->(p:NonTimberProduct)-[:LIMITED_BY]->(q:NonTimberCollectionLimit)
WITH p, q,
     count(c) AS compartmentCount,
     round(avg(yp.confidence), 2) AS avgConfidence,
     collect(c.unitCode) AS compartments
RETURN p.name AS product,
       p.category AS category,
       q.limitValue AS limitValue,
       q.unit AS unit,
       q.period AS period,
       compartmentCount,
       avgConfidence,
       compartments
ORDER BY compartmentCount DESC, product ASC;
