// CQ9 (Аналіз впливу №1): Залежності від загрози на глибину >= 3 (шляхи змінної довжини).
// Простежує каскадний вплив: Threat -[:TRIGGERS]-> Process -[:FOLLOWED_BY|APPLIED_TO|PART_OF_FORESTRY*2..3]-> target
// Конструкції: шлях змінної довжини (*3..4), reduce() для мінімальної довіри (confidence) на шляху, WITH, nodes()/relationships().
MATCH path = (t:Threat)-[:TRIGGERS|FOLLOWED_BY|APPLIED_TO|PART_OF_FORESTRY*3..4]->(target:Forestry)
WITH t, target, path,
     length(path) AS depth,
     [n IN nodes(path) | coalesce(n.unitCode, n.id)] AS chainNodes,
     [r IN relationships(path) | type(r)] AS chainRelTypes,
     reduce(minConf = 1.0, r IN relationships(path) |
            CASE WHEN r.confidence < minConf THEN r.confidence ELSE minConf END) AS minPathConfidence
RETURN t.id AS threatId,
       t.name AS threatName,
       target.unitCode AS affectedForestry,
       depth,
       minPathConfidence,
       chainNodes,
       chainRelTypes
ORDER BY depth DESC, threatId ASC, affectedForestry ASC;
