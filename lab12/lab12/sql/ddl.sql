-- Лабораторна робота 12: Зіркова схема OLAP-куба (DuckDB DDL)
-- ПдО: Управління лісовими продуктами (Domain Knowledge Hub)
-- Зерно факту: 1 подія заготівлі / збору конкретного лісового продукту (IRI)
-- на конкретному виділі у конкретну дату конкретним виконавцем за одним дозволом.

CREATE TABLE IF NOT EXISTS dim_date (
    date_sk INTEGER PRIMARY KEY,          -- YYYYMMDD
    full_date DATE NOT NULL UNIQUE,
    year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,             -- 1..4
    quarter_label VARCHAR NOT NULL,       -- 'Q1'..'Q4'
    month INTEGER NOT NULL,               -- 1..12
    month_name_uk VARCHAR NOT NULL,
    year_month VARCHAR NOT NULL,          -- 'YYYY-MM'
    season VARCHAR NOT NULL,              -- 'Зима', 'Весна', 'Літо', 'Осінь'
    is_fire_hazard_season BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_product_taxonomy (
    product_sk INTEGER PRIMARY KEY,
    product_iri VARCHAR NOT NULL UNIQUE,  -- IRI з таксономії ЛР 5
    parent_iri VARCHAR NOT NULL,
    skos_notation VARCHAR NOT NULL,
    top_class_uk VARCHAR NOT NULL,        -- Рівень 1: 'Деревинні продукти' / 'Недеревинні продукти'
    subclass_uk VARCHAR NOT NULL,         -- Рівень 2: 'Хвойна деревина', 'Листяна деревина', 'Гриби', ...
    product_name_uk VARCHAR NOT NULL,     -- Рівень 3: конкретний продукт
    unit_base VARCHAR NOT NULL,           -- 'м³' або 'кг'
    fsc_eligible BOOLEAN NOT NULL,
    ref_price_uah DOUBLE NOT NULL,
    scd_type VARCHAR NOT NULL DEFAULT 'SCD1',
    updated_at DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_location (
    location_sk INTEGER PRIMARY KEY,
    compartment_code VARCHAR NOT NULL,    -- V-001 .. V-206
    compartment_name VARCHAR NOT NULL,
    forestry_code VARCHAR NOT NULL,       -- LS-01 .. LS-04
    forestry_name VARCHAR NOT NULL,       -- Лісництво «Карпатське» тощо
    region_name VARCHAR NOT NULL,         -- Львівська / Івано-Франківська обл.
    area_ha DOUBLE NOT NULL,
    dominant_species VARCHAR NOT NULL,
    annual_increment_m3 DOUBLE NOT NULL,
    ndvi_band VARCHAR NOT NULL,           -- 'Високий (>=0.75)', 'Середній (0.60-0.75)', 'Низький (<0.60)'
    fsc_certified BOOLEAN NOT NULL,
    -- SCD Type 2 поля
    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL,
    is_current BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_actor (
    actor_sk INTEGER PRIMARY KEY,
    actor_id VARCHAR NOT NULL,
    staff_code VARCHAR NOT NULL,          -- F-101..F-402, BR-01..BR-03
    actor_name VARCHAR NOT NULL,
    actor_type VARCHAR NOT NULL,          -- 'Forester' або 'HarvestBrigade'
    forestry_code VARCHAR NOT NULL,
    qualification_level VARCHAR NOT NULL,
    -- SCD Type 2 поля для переведень між лісництвами
    valid_from DATE NOT NULL,
    valid_to DATE NOT NULL,
    is_current BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_permit (
    permit_sk INTEGER PRIMARY KEY,
    permit_code VARCHAR NOT NULL UNIQUE,  -- LK-2024-001 ..
    permit_type VARCHAR NOT NULL,         -- 'Лісорубний квиток', 'Лісовий квиток (НДП)', 'Санітарний дозвіл'
    eco_risk_level VARCHAR NOT NULL,      -- 'Низький', 'Середній', 'Високий'
    quota_limit_m3 DOUBLE NOT NULL,
    issued_year INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_forest_harvest (
    fact_id BIGINT PRIMARY KEY,
    date_sk INTEGER NOT NULL REFERENCES dim_date(date_sk),
    product_sk INTEGER NOT NULL REFERENCES dim_product_taxonomy(product_sk),
    location_sk INTEGER NOT NULL REFERENCES dim_location(location_sk),
    actor_sk INTEGER NOT NULL REFERENCES dim_actor(actor_sk),
    permit_sk INTEGER NOT NULL REFERENCES dim_permit(permit_sk),
    -- Адитивні міри
    volume_m3 DOUBLE NOT NULL,            -- >0 для деревини, 0 для НДП
    mass_kg DOUBLE NOT NULL,              -- >0 для НДП, 0 для деревини
    revenue_uah DOUBLE NOT NULL,
    cost_uah DOUBLE NOT NULL,
    margin_uah DOUBLE NOT NULL,
    event_count INTEGER NOT NULL DEFAULT 1,
    -- Напівадитивні міри (неадитивні за часом)
    remaining_quota_m3 DOUBLE NOT NULL,
    standing_stock_m3 DOUBLE NOT NULL,
    -- Неадитивні міри (перераховуються через відношення сум або середнє)
    unit_price_uah DOUBLE NOT NULL,
    margin_pct DOUBLE NOT NULL,
    damaged_trees_share_pct DOUBLE NOT NULL,
    ndvi_score DOUBLE NOT NULL
);
