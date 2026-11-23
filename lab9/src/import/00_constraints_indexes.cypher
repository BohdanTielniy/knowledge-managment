// ЛР 9, Результат 2. Обмеження унікальності та індекси.
// Виконується ДО імпорту; IF NOT EXISTS робить скрипт ідемпотентним.

// --- Унікальні обмеження (id кожної мітки) ---
CREATE CONSTRAINT forestry_id IF NOT EXISTS FOR (n:Forestry) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT compartment_id IF NOT EXISTS FOR (n:Compartment) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT treespecies_id IF NOT EXISTS FOR (n:TreeSpecies) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT forestproduct_id IF NOT EXISTS FOR (n:ForestProduct) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT threat_id IF NOT EXISTS FOR (n:Threat) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT meteo_id IF NOT EXISTS FOR (n:MeteoObservation) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT process_id IF NOT EXISTS FOR (n:Process) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT permit_id IF NOT EXISTS FOR (n:Permit) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT quota_id IF NOT EXISTS FOR (n:Quota) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT actor_id IF NOT EXISTS FOR (n:Actor) REQUIRE n.id IS UNIQUE;

// --- Бізнес-ключі (аналог fm:unitCode з ЛР 6–8) ---
CREATE CONSTRAINT forestry_code IF NOT EXISTS FOR (n:Forestry) REQUIRE n.unitCode IS UNIQUE;
CREATE CONSTRAINT compartment_code IF NOT EXISTS FOR (n:Compartment) REQUIRE n.unitCode IS UNIQUE;

// --- Індекси під запити (пороги правил R5, R8, KQ4, KQ8) ---
CREATE INDEX compartment_damage IF NOT EXISTS FOR (n:Compartment) ON (n.damagedTreesShare);
CREATE INDEX compartment_ndvi IF NOT EXISTS FOR (n:Compartment) ON (n.ndviValue);
CREATE INDEX compartment_age IF NOT EXISTS FOR (n:Compartment) ON (n.standAgeYears);
CREATE INDEX meteo_date IF NOT EXISTS FOR (n:MeteoObservation) ON (n.observationDate);

// --- Фіксація стану (скриншот/вивід у звіт) ---
SHOW CONSTRAINTS;
SHOW INDEXES;
