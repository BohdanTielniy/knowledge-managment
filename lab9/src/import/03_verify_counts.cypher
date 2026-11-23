// Результат 2, крок 4: кількості вузлів і зв'язків (порівнюються до/після повторного імпорту).

MATCH (n) RETURN count(n) AS nodes;

MATCH ()-[r]->() RETURN count(r) AS relationships;

MATCH (n) UNWIND labels(n) AS label
RETURN label, count(*) AS cnt ORDER BY label;

MATCH ()-[r]->() RETURN type(r) AS relType, count(*) AS cnt ORDER BY relType;

// Усі зв'язки мають властивості походження (очікується 0)
MATCH ()-[r]->()
WHERE r.source IS NULL OR r.confidence IS NULL OR r.validFrom IS NULL
RETURN count(r) AS relsWithoutProvenance;

// Частка даних за походженням
MATCH ()-[r]->() RETURN r.source AS source, r.confidence AS confidence, count(*) AS cnt ORDER BY source;
