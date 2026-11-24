// ЛР 9, Результат 4: Graph Data Science (PageRank + Louvain) та збереження властивостей у графі.

// 1. Перевірка версії GDS
RETURN gds.version() AS gdsVersion;

// 2. Видалення попередніх проєкцій (ідемпотентність)
CALL gds.graph.drop('forest_directed', false) YIELD graphName;
CALL gds.graph.drop('forest_undirected', false) YIELD graphName;

// 3. Орієнтована проєкція для PageRank (усі 166 вузлів і 333 зв'язки)
CALL gds.graph.project(
  'forest_directed',
  '*',
  '*'
) YIELD graphName, nodeCount, relationshipCount;

// 4. PageRank: топ-10 вузлів (stream)
CALL gds.pageRank.stream('forest_directed', {
  maxIterations: 20,
  dampingFactor: 0.85
})
YIELD nodeId, score
WITH gds.util.asNode(nodeId) AS n, round(score, 4) AS pagerank
RETURN n.id AS nodeId,
       labels(n)[0] AS primaryLabel,
       coalesce(n.name, n.number, n.id) AS displayName,
       pagerank
ORDER BY pagerank DESC, nodeId ASC
LIMIT 10;

// 5. Збереження PageRank у властивість вузлів (n.pagerank) — Крок 4 (C4)
CALL gds.pageRank.write('forest_directed', {
  maxIterations: 20,
  dampingFactor: 0.85,
  writeProperty: 'pagerank'
})
YIELD nodePropertiesWritten, ranIterations, didConverge;

// 6. Неорієнтована проєкція для Louvain (усі мітки та зв'язки з орієнтацією UNDIRECTED)
CALL gds.graph.project(
  'forest_undirected',
  '*',
  {
    ALL_RELS: {
      type: '*',
      orientation: 'UNDIRECTED'
    }
  }
) YIELD graphName, nodeCount, relationshipCount;

// 7. Louvain: виявлення спільнот (stream + агрегація розміру та ключових вузлів)
CALL gds.louvain.stream('forest_undirected', {
  seedProperty: null
})
YIELD nodeId, communityId
WITH communityId, collect(gds.util.asNode(nodeId)) AS members
RETURN communityId,
       size(members) AS communitySize,
       [m IN members WHERE m:Forestry | m.unitCode] AS forestries,
       [m IN members | m.id][0..5] AS sampleNodes
ORDER BY communitySize DESC;

// 8. Збереження спільнот у властивість вузлів (n.community) — Крок 4 (C4)
CALL gds.louvain.write('forest_undirected', {
  writeProperty: 'community'
})
YIELD communityCount, modularity, nodePropertiesWritten;

// 9. Перевірка збереження властивостей у графі (очікується 166 вузлів)
MATCH (n)
WHERE n.pagerank IS NOT NULL AND n.community IS NOT NULL
RETURN count(n) AS nodesWithGdsProps,
       count(DISTINCT n.community) AS distinctCommunities,
       round(max(n.pagerank), 4) AS maxPagerank,
       round(min(n.pagerank), 4) AS minPagerank;

// 10. Очищення проєкцій у пам'яті GDS
CALL gds.graph.drop('forest_directed', false) YIELD graphName;
CALL gds.graph.drop('forest_undirected', false) YIELD graphName;
