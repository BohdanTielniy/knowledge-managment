// ЛР 9. Імпорт вузлів (ідемпотентний: MERGE за унікальним id).
// Файли CSV монтуються у каталог import контейнера Neo4j (див. docker-compose.yml).

// Forestry
LOAD CSV WITH HEADERS FROM 'file:///nodes_forestry.csv' AS row
MERGE (n:Forestry {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.unitCode = CASE row.unitCode WHEN '' THEN null ELSE row.unitCode END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.areaHectares = CASE row.areaHectares WHEN '' THEN null ELSE toFloat(row.areaHectares) END;

// Compartment
LOAD CSV WITH HEADERS FROM 'file:///nodes_compartment.csv' AS row
MERGE (n:Compartment {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.unitCode = CASE row.unitCode WHEN '' THEN null ELSE row.unitCode END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.areaHectares = CASE row.areaHectares WHEN '' THEN null ELSE toFloat(row.areaHectares) END,
    n.standAgeYears = CASE row.standAgeYears WHEN '' THEN null ELSE toInteger(row.standAgeYears) END,
    n.dbhCm = CASE row.dbhCm WHEN '' THEN null ELSE toFloat(row.dbhCm) END,
    n.heightMeters = CASE row.heightMeters WHEN '' THEN null ELSE toFloat(row.heightMeters) END,
    n.timberStockM3 = CASE row.timberStockM3 WHEN '' THEN null ELSE toFloat(row.timberStockM3) END,
    n.annualIncrementM3 = CASE row.annualIncrementM3 WHEN '' THEN null ELSE toFloat(row.annualIncrementM3) END,
    n.damagedTreesShare = CASE row.damagedTreesShare WHEN '' THEN null ELSE toFloat(row.damagedTreesShare) END,
    n.ndviValue = CASE row.ndviValue WHEN '' THEN null ELSE toFloat(row.ndviValue) END;

// TreeSpecies:ConiferousSpecies
LOAD CSV WITH HEADERS FROM 'file:///nodes_treespecies.csv' AS row
WITH row WHERE row.subtype = 'ConiferousSpecies'
MERGE (n:TreeSpecies:ConiferousSpecies {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.latinName = CASE row.latinName WHEN '' THEN null ELSE row.latinName END;

// TreeSpecies:DeciduousSpecies
LOAD CSV WITH HEADERS FROM 'file:///nodes_treespecies.csv' AS row
WITH row WHERE row.subtype = 'DeciduousSpecies'
MERGE (n:TreeSpecies:DeciduousSpecies {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.latinName = CASE row.latinName WHEN '' THEN null ELSE row.latinName END;

// ForestProduct:TimberProduct
LOAD CSV WITH HEADERS FROM 'file:///nodes_forestproduct.csv' AS row
WITH row WHERE row.subtype = 'TimberProduct'
MERGE (n:ForestProduct:TimberProduct {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.category = CASE row.category WHEN '' THEN null ELSE row.category END;

// ForestProduct:NonTimberProduct
LOAD CSV WITH HEADERS FROM 'file:///nodes_forestproduct.csv' AS row
WITH row WHERE row.subtype = 'NonTimberProduct'
MERGE (n:ForestProduct:NonTimberProduct {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.category = CASE row.category WHEN '' THEN null ELSE row.category END;

// Threat:InsectPest
LOAD CSV WITH HEADERS FROM 'file:///nodes_threat.csv' AS row
WITH row WHERE row.subtype = 'InsectPest'
MERGE (n:Threat:InsectPest {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.kind = CASE row.kind WHEN '' THEN null ELSE row.kind END,
    n.detectedOn = CASE row.detectedOn WHEN '' THEN null ELSE date(row.detectedOn) END;

// Threat:ForestDisease
LOAD CSV WITH HEADERS FROM 'file:///nodes_threat.csv' AS row
WITH row WHERE row.subtype = 'ForestDisease'
MERGE (n:Threat:ForestDisease {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.kind = CASE row.kind WHEN '' THEN null ELSE row.kind END,
    n.detectedOn = CASE row.detectedOn WHEN '' THEN null ELSE date(row.detectedOn) END;

// Threat:Drought
LOAD CSV WITH HEADERS FROM 'file:///nodes_threat.csv' AS row
WITH row WHERE row.subtype = 'Drought'
MERGE (n:Threat:Drought {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.kind = CASE row.kind WHEN '' THEN null ELSE row.kind END,
    n.detectedOn = CASE row.detectedOn WHEN '' THEN null ELSE date(row.detectedOn) END;

// Threat:Windthrow
LOAD CSV WITH HEADERS FROM 'file:///nodes_threat.csv' AS row
WITH row WHERE row.subtype = 'Windthrow'
MERGE (n:Threat:Windthrow {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.kind = CASE row.kind WHEN '' THEN null ELSE row.kind END,
    n.detectedOn = CASE row.detectedOn WHEN '' THEN null ELSE date(row.detectedOn) END;

// MeteoObservation
LOAD CSV WITH HEADERS FROM 'file:///nodes_meteoobservation.csv' AS row
MERGE (n:MeteoObservation {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.observationDate = CASE row.observationDate WHEN '' THEN null ELSE date(row.observationDate) END,
    n.airTemperatureC = CASE row.airTemperatureC WHEN '' THEN null ELSE toFloat(row.airTemperatureC) END,
    n.airHumidityPercent = CASE row.airHumidityPercent WHEN '' THEN null ELSE toFloat(row.airHumidityPercent) END,
    n.daysWithoutRain = CASE row.daysWithoutRain WHEN '' THEN null ELSE toInteger(row.daysWithoutRain) END,
    n.soilMoisturePercent = CASE row.soilMoisturePercent WHEN '' THEN null ELSE toFloat(row.soilMoisturePercent) END;

// Process:SanitaryFelling
LOAD CSV WITH HEADERS FROM 'file:///nodes_process.csv' AS row
WITH row WHERE row.subtype = 'SanitaryFelling'
MERGE (n:Process:TimberHarvesting:SanitaryFelling {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.plannedDate = CASE row.plannedDate WHEN '' THEN null ELSE date(row.plannedDate) END,
    n.harvestVolumeM3 = CASE row.harvestVolumeM3 WHEN '' THEN null ELSE toFloat(row.harvestVolumeM3) END,
    n.plantedSeedlingsCount = CASE row.plantedSeedlingsCount WHEN '' THEN null ELSE toInteger(row.plantedSeedlingsCount) END;

// Process:MainFelling
LOAD CSV WITH HEADERS FROM 'file:///nodes_process.csv' AS row
WITH row WHERE row.subtype = 'MainFelling'
MERGE (n:Process:TimberHarvesting:MainFelling {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.plannedDate = CASE row.plannedDate WHEN '' THEN null ELSE date(row.plannedDate) END,
    n.harvestVolumeM3 = CASE row.harvestVolumeM3 WHEN '' THEN null ELSE toFloat(row.harvestVolumeM3) END,
    n.plantedSeedlingsCount = CASE row.plantedSeedlingsCount WHEN '' THEN null ELSE toInteger(row.plantedSeedlingsCount) END;

// Process:Reforestation
LOAD CSV WITH HEADERS FROM 'file:///nodes_process.csv' AS row
WITH row WHERE row.subtype = 'Reforestation'
MERGE (n:Process:Reforestation {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.plannedDate = CASE row.plannedDate WHEN '' THEN null ELSE date(row.plannedDate) END,
    n.harvestVolumeM3 = CASE row.harvestVolumeM3 WHEN '' THEN null ELSE toFloat(row.harvestVolumeM3) END,
    n.plantedSeedlingsCount = CASE row.plantedSeedlingsCount WHEN '' THEN null ELSE toInteger(row.plantedSeedlingsCount) END;

// Process:FirePreventionMeasure
LOAD CSV WITH HEADERS FROM 'file:///nodes_process.csv' AS row
WITH row WHERE row.subtype = 'FirePreventionMeasure'
MERGE (n:Process:FirePreventionMeasure {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.plannedDate = CASE row.plannedDate WHEN '' THEN null ELSE date(row.plannedDate) END,
    n.harvestVolumeM3 = CASE row.harvestVolumeM3 WHEN '' THEN null ELSE toFloat(row.harvestVolumeM3) END,
    n.plantedSeedlingsCount = CASE row.plantedSeedlingsCount WHEN '' THEN null ELSE toInteger(row.plantedSeedlingsCount) END;

// Permit:FellingTicket
LOAD CSV WITH HEADERS FROM 'file:///nodes_permit.csv' AS row
WITH row WHERE row.subtype = 'FellingTicket'
MERGE (n:Permit:FellingTicket {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.number = CASE row.number WHEN '' THEN null ELSE row.number END,
    n.issuedOn = CASE row.issuedOn WHEN '' THEN null ELSE date(row.issuedOn) END;

// Quota:HarvestQuota
LOAD CSV WITH HEADERS FROM 'file:///nodes_quota.csv' AS row
WITH row WHERE row.subtype = 'HarvestQuota'
MERGE (n:Quota:HarvestQuota {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.limitValue = CASE row.limitValue WHEN '' THEN null ELSE toFloat(row.limitValue) END,
    n.unit = CASE row.unit WHEN '' THEN null ELSE row.unit END,
    n.period = CASE row.period WHEN '' THEN null ELSE row.period END;

// Quota:NonTimberCollectionLimit
LOAD CSV WITH HEADERS FROM 'file:///nodes_quota.csv' AS row
WITH row WHERE row.subtype = 'NonTimberCollectionLimit'
MERGE (n:Quota:NonTimberCollectionLimit {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.limitValue = CASE row.limitValue WHEN '' THEN null ELSE toFloat(row.limitValue) END,
    n.unit = CASE row.unit WHEN '' THEN null ELSE row.unit END,
    n.period = CASE row.period WHEN '' THEN null ELSE row.period END;

// Actor:Forester
LOAD CSV WITH HEADERS FROM 'file:///nodes_actor.csv' AS row
WITH row WHERE row.subtype = 'Forester'
MERGE (n:Actor:Forester {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.staffCode = CASE row.staffCode WHEN '' THEN null ELSE row.staffCode END;

// Actor:ChiefForester
LOAD CSV WITH HEADERS FROM 'file:///nodes_actor.csv' AS row
WITH row WHERE row.subtype = 'ChiefForester'
MERGE (n:Actor:ChiefForester {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.staffCode = CASE row.staffCode WHEN '' THEN null ELSE row.staffCode END;

// Actor:HarvestBrigade
LOAD CSV WITH HEADERS FROM 'file:///nodes_actor.csv' AS row
WITH row WHERE row.subtype = 'HarvestBrigade'
MERGE (n:Actor:HarvestBrigade {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.staffCode = CASE row.staffCode WHEN '' THEN null ELSE row.staffCode END;

// Actor:EmergencyService
LOAD CSV WITH HEADERS FROM 'file:///nodes_actor.csv' AS row
WITH row WHERE row.subtype = 'EmergencyService'
MERGE (n:Actor:EmergencyService {id: row.id})
SET n.origin = CASE row.origin WHEN '' THEN null ELSE row.origin END,
    n.name = CASE row.name WHEN '' THEN null ELSE row.name END,
    n.staffCode = CASE row.staffCode WHEN '' THEN null ELSE row.staffCode END;
