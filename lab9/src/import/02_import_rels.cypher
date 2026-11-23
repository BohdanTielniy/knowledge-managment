// ЛР 9. Імпорт зв'язків із властивостями походження (source, confidence, validFrom).
// MERGE за шаблоном (a)-[:TYPE]->(b) гарантує відсутність дублікатів при повторному запуску.

// PART_OF_FORESTRY: Compartment -> Forestry
LOAD CSV WITH HEADERS FROM 'file:///rels_PART_OF_FORESTRY.csv' AS row
WITH row WHERE row.start_label = 'Compartment' AND row.end_label = 'Forestry'
MATCH (a:Compartment {id: row.start_id})
MATCH (b:Forestry {id: row.end_id})
MERGE (a)-[r:PART_OF_FORESTRY]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// HAS_DOMINANT_SPECIES: Compartment -> TreeSpecies
LOAD CSV WITH HEADERS FROM 'file:///rels_HAS_DOMINANT_SPECIES.csv' AS row
WITH row WHERE row.start_label = 'Compartment' AND row.end_label = 'TreeSpecies'
MATCH (a:Compartment {id: row.start_id})
MATCH (b:TreeSpecies {id: row.end_id})
MERGE (a)-[r:HAS_DOMINANT_SPECIES]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// YIELDS_PRODUCT: Compartment -> ForestProduct
LOAD CSV WITH HEADERS FROM 'file:///rels_YIELDS_PRODUCT.csv' AS row
WITH row WHERE row.start_label = 'Compartment' AND row.end_label = 'ForestProduct'
MATCH (a:Compartment {id: row.start_id})
MATCH (b:ForestProduct {id: row.end_id})
MERGE (a)-[r:YIELDS_PRODUCT]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// AFFECTED_BY: Compartment -> Threat
LOAD CSV WITH HEADERS FROM 'file:///rels_AFFECTED_BY.csv' AS row
WITH row WHERE row.start_label = 'Compartment' AND row.end_label = 'Threat'
MATCH (a:Compartment {id: row.start_id})
MATCH (b:Threat {id: row.end_id})
MERGE (a)-[r:AFFECTED_BY]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// TRIGGERS: MeteoObservation -> Process
LOAD CSV WITH HEADERS FROM 'file:///rels_TRIGGERS.csv' AS row
WITH row WHERE row.start_label = 'MeteoObservation' AND row.end_label = 'Process'
MATCH (a:MeteoObservation {id: row.start_id})
MATCH (b:Process {id: row.end_id})
MERGE (a)-[r:TRIGGERS]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// TRIGGERS: Threat -> Process
LOAD CSV WITH HEADERS FROM 'file:///rels_TRIGGERS.csv' AS row
WITH row WHERE row.start_label = 'Threat' AND row.end_label = 'Process'
MATCH (a:Threat {id: row.start_id})
MATCH (b:Process {id: row.end_id})
MERGE (a)-[r:TRIGGERS]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// APPLIED_TO: Process -> Compartment
LOAD CSV WITH HEADERS FROM 'file:///rels_APPLIED_TO.csv' AS row
WITH row WHERE row.start_label = 'Process' AND row.end_label = 'Compartment'
MATCH (a:Process {id: row.start_id})
MATCH (b:Compartment {id: row.end_id})
MERGE (a)-[r:APPLIED_TO]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// REQUIRES_PERMIT: Process -> Permit
LOAD CSV WITH HEADERS FROM 'file:///rels_REQUIRES_PERMIT.csv' AS row
WITH row WHERE row.start_label = 'Process' AND row.end_label = 'Permit'
MATCH (a:Process {id: row.start_id})
MATCH (b:Permit {id: row.end_id})
MERGE (a)-[r:REQUIRES_PERMIT]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// CONSTRAINED_BY: Process -> Quota
LOAD CSV WITH HEADERS FROM 'file:///rels_CONSTRAINED_BY.csv' AS row
WITH row WHERE row.start_label = 'Process' AND row.end_label = 'Quota'
MATCH (a:Process {id: row.start_id})
MATCH (b:Quota {id: row.end_id})
MERGE (a)-[r:CONSTRAINED_BY]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// PERFORMED_BY: Process -> Actor
LOAD CSV WITH HEADERS FROM 'file:///rels_PERFORMED_BY.csv' AS row
WITH row WHERE row.start_label = 'Process' AND row.end_label = 'Actor'
MATCH (a:Process {id: row.start_id})
MATCH (b:Actor {id: row.end_id})
MERGE (a)-[r:PERFORMED_BY]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// SUPERVISES: Actor -> Compartment
LOAD CSV WITH HEADERS FROM 'file:///rels_SUPERVISES.csv' AS row
WITH row WHERE row.start_label = 'Actor' AND row.end_label = 'Compartment'
MATCH (a:Actor {id: row.start_id})
MATCH (b:Compartment {id: row.end_id})
MERGE (a)-[r:SUPERVISES]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// SUPERVISES: Actor -> Forestry
LOAD CSV WITH HEADERS FROM 'file:///rels_SUPERVISES.csv' AS row
WITH row WHERE row.start_label = 'Actor' AND row.end_label = 'Forestry'
MATCH (a:Actor {id: row.start_id})
MATCH (b:Forestry {id: row.end_id})
MERGE (a)-[r:SUPERVISES]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// NOTIFIES: Process -> Actor
LOAD CSV WITH HEADERS FROM 'file:///rels_NOTIFIES.csv' AS row
WITH row WHERE row.start_label = 'Process' AND row.end_label = 'Actor'
MATCH (a:Process {id: row.start_id})
MATCH (b:Actor {id: row.end_id})
MERGE (a)-[r:NOTIFIES]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// FOLLOWED_BY: Process -> Process
LOAD CSV WITH HEADERS FROM 'file:///rels_FOLLOWED_BY.csv' AS row
WITH row WHERE row.start_label = 'Process' AND row.end_label = 'Process'
MATCH (a:Process {id: row.start_id})
MATCH (b:Process {id: row.end_id})
MERGE (a)-[r:FOLLOWED_BY]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// MONITORS_UNIT: MeteoObservation -> Forestry
LOAD CSV WITH HEADERS FROM 'file:///rels_MONITORS_UNIT.csv' AS row
WITH row WHERE row.start_label = 'MeteoObservation' AND row.end_label = 'Forestry'
MATCH (a:MeteoObservation {id: row.start_id})
MATCH (b:Forestry {id: row.end_id})
MERGE (a)-[r:MONITORS_UNIT]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);

// LIMITED_BY: ForestProduct -> Quota
LOAD CSV WITH HEADERS FROM 'file:///rels_LIMITED_BY.csv' AS row
WITH row WHERE row.start_label = 'ForestProduct' AND row.end_label = 'Quota'
MATCH (a:ForestProduct {id: row.start_id})
MATCH (b:Quota {id: row.end_id})
MERGE (a)-[r:LIMITED_BY]->(b)
SET r.source = row.source, r.confidence = toFloat(row.confidence), r.validFrom = date(row.validFrom);
