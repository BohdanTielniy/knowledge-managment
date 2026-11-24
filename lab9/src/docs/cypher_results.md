# Результат 3. Запити Cypher, результати та ручна верифікація

Усі 10 запитів збережено у каталозі `queries/` (`q01_cq1_damaged_compartments.cypher` … `q10_cq10_impact_quota_shortest_path.cypher`).
Автоматичний запуск у Neo4j: `bash scripts/run_queries.sh`.
Незалежна перевірка еталонних результатів на CSV: `python3 scripts/verify_queries_and_gds.py`.

## Покриття конструкцій Cypher (C1, C3)

| Файл запиту | CQ | Основні конструкції Cypher |
|-------------|----|----------------------------|
| `q01_cq1_damaged_compartments.cypher` | CQ1 | `MATCH` (багатокроковий шаблон), `WHERE`, `ORDER BY`, властивості походження зв'язку |
| `q02_cq2_high_fire_risk.cypher` | CQ2 | `MATCH`, `OPTIONAL MATCH`, складний фільтр `AND`, `collect(DISTINCT ...)` |
| `q03_cq3_planned_fellings.cypher` | CQ3 | Мітка надкласу `:TimberHarvesting`, `WITH`, обчислювані булеві поля, `CASE` |
| `q04_cq4_mature_coniferous.cypher` | CQ4 | Підмітка `:ConiferousSpecies`, `WITH`, агрегації `count`, `sum`, `avg`, `min`, `collect` |
| `q05_cq5_reforestation_check.cypher` | CQ5 | `OPTIONAL MATCH`, перевірка `IS NULL`, `WITH`, `CASE` |
| `q06_cq6_foresters_threats_fire.cypher` | CQ6 | Подвійний `OPTIONAL MATCH`, `WITH`, `size()`, агрегація двох контурів |
| `q07_cq7_nontimber_limits.cypher` | CQ7 | Підмітки `:NonTimberProduct` / `:NonTimberCollectionLimit`, `WITH`, `count`, `avg`, `collect` |
| `q08_cq8_low_ndvi_inspection.cypher` | CQ8 | Індексована фільтрація (`compartment_ndvi`), `OPTIONAL MATCH`, `CASE` |
| `q09_cq9_impact_threat_chain.cypher` | CQ9 (вплив №1) | Шлях змінної довжини `[*3..4]`, `length(path)`, `nodes()`, `relationships()`, `reduce()` |
| `q10_cq10_impact_quota_shortest_path.cypher` | CQ10 (вплив №2) | Каскадний аналіз впливу (глибина 3+) та `shortestPath((fo)-[*1..6]-(t))` |

---

## Запити, результати та інтерпретація (C2)

### CQ1 — Уражені виділи (> 10 %) та активні загрози (`queries/q01_cq1_damaged_compartments.cypher`)

```cypher
MATCH (c:Compartment)-[:PART_OF_FORESTRY]->(f:Forestry),
      (c)-[:HAS_DOMINANT_SPECIES]->(s:TreeSpecies),
      (c)-[r:AFFECTED_BY]->(t:Threat)
WHERE c.damagedTreesShare > 10.0
RETURN c.unitCode AS compartment, f.unitCode AS forestry, s.name AS dominantSpecies,
       c.damagedTreesShare AS damagedPct, t.name AS threat,
       r.source AS source, r.confidence AS confidence
ORDER BY damagedPct DESC, compartment ASC;
```

**Результат (7 виділів):**

| compartment | forestry | dominantSpecies | damagedPct | threat | source | confidence |
|-------------|----------|-----------------|-----------:|--------|--------|-----------:|
| V-207 | LS-03 | Ялина європейська | 28.7 | Короїд-типограф (Ips typographus) | synthetic-gen-seed42 | 0.8 |
| V-107 | LS-02 | Ялина європейська | 23.3 | Короїд-типограф (Ips typographus) | synthetic-gen-seed42 | 0.8 |
| V-014 | LS-01 | Ялиця біла | 19.6 | Кореневе гниття (Heterobasidion annosum) | synthetic-gen-seed42 | 0.8 |
| V-203 | LS-03 | Ялина європейська | 18.4 | Короїд-типограф (Ips typographus) | synthetic-gen-seed42 | 0.8 |
| V-009 | LS-01 | Ялиця біла | 15.6 | Кореневе гниття (Heterobasidion annosum) | synthetic-gen-seed42 | 0.8 |
| V-302 | LS-04 | Ялина європейська | 15.0 | Кореневе гниття (Heterobasidion annosum) | synthetic-gen-seed42 | 0.8 |
| V-012 | LS-01 | Ялина європейська | 12.0 | Короїд-типограф (Ips typographus) | lab7-8-abox | 1.0 |

**Інтерпретація:** Усі 7 критично уражених виділів — хвойні насадження (ялина європейська або ялиця біла), уражені біотичними загрозами (короїд-типограф або кореневе гниття). Найвища частка ураження зафіксована у Верховинському лісництві (`V-207`, 28.7 %). Базовий виділ `V-012` із ЛР 7–8 має найвищу довіру `confidence = 1.0`.

### CQ2 — Метеозаміри високого пожежного ризику (`queries/q02_cq2_high_fire_risk.cypher`)

```cypher
MATCH (o:MeteoObservation)-[m:MONITORS_UNIT]->(f:Forestry)
WHERE o.airTemperatureC > 30.0 AND o.airHumidityPercent < 30.0 AND o.daysWithoutRain >= 7
OPTIONAL MATCH (a:Forester)-[:SUPERVISES]->(f)
RETURN o.observationDate AS obsDate, f.unitCode AS forestryCode, f.name AS forestryName,
       o.airTemperatureC AS tempC, o.airHumidityPercent AS humidityPct,
       o.daysWithoutRain AS dryDays, collect(DISTINCT a.name) AS supervisingForesters,
       m.validFrom AS validFrom
ORDER BY obsDate ASC;
```

**Результат (4 заміри):**

| obsDate | forestryCode | forestryName | tempC | humidityPct | dryDays | supervisingForesters | validFrom |
|---------|--------------|--------------|------:|------------:|--------:|----------------------|-----------|
| 2026-09-04 | LS-02 | Лісництво «Бескидське» | 31.7 | 22.7 | 12 | `[]` | 2026-09-04 |
| 2026-09-05 | LS-01 | Лісництво «Карпатське» | 31.0 | 27.0 | 9 | `["Фомін О.В."]` | 2026-09-05 |
| 2026-09-11 | LS-03 | Лісництво «Верховинське» | 31.6 | 20.7 | 8 | `[]` | 2026-09-11 |
| 2026-09-16 | LS-04 | Лісництво «Дністровське» | 32.2 | 26.3 | 14 | `[]` | 2026-09-16 |

**Інтерпретація:** Усі 4 лісництва пережили пік пожежної небезпеки у першій половині вересня 2026 р. (пороги правила R8 з ЛР 7: $T > 30\,^\circ\text{C}$, вологість $< 30\,\%$, $\ge 7$ діб без опадів). Прямий зв'язок `:Forester-[:SUPERVISES]->:Forestry` наявний лише у `LS-01` (Фомін О.В.), тоді як у `LS-02..LS-04` нагляд за лісництвом здійснює `:ChiefForester`, що й демонструє роль `OPTIONAL MATCH` (рядки не губляться).

### CQ3 — Заплановані рубки, обсяги, дозволи та контроль квот (`queries/q03_cq3_planned_fellings.cypher`)

**Результат (13 рубок, сумарний обсяг 3247.0 м³):**

| processId | fellingType | compartment | volumeM3 | quotaM3 | exceedsQuota | permitNumber | actor |
|-----------|-------------|-------------|---------:|--------:|:------------:|--------------|-------|
| MainFelling_2026_V102 | MainFelling | V-102 | 694.0 | 620.0 | **true** | ЛК-2026-047 | Бригада лісозаготівлі №3 |
| MainFelling_2026_V204 | MainFelling | V-204 | 457.0 | 660.0 | false | ЛК-2026-049 | Бригада лісозаготівлі №1 |
| MainFelling_2026_V013 | MainFelling | V-013 | 306.0 | 430.0 | false | ЛК-2026-051 | Бригада лісозаготівлі №2 |
| MainFelling_2026_V003 | MainFelling | V-003 | 260.0 | 300.0 | false | ЛК-2026-039 | Бригада лісозаготівлі №1 |
| MainFelling_2026_V208 | MainFelling | V-208 | 230.0 | 370.0 | false | ЛК-2026-048 | Бригада лісозаготівлі №3 |
| MainFelling_2026_V206 | MainFelling | V-206 | 221.0 | 320.0 | false | ЛК-2026-050 | Бригада лісозаготівлі №1 |
| SanitaryFelling_2026_V302 | SanitaryFelling | V-302 | 192.0 | 230.0 | false | ЛК-2026-041 | Лісник F-401 |
| SanitaryFelling_2026_V107 | SanitaryFelling | V-107 | 185.0 | 280.0 | false | ЛК-2026-040 | Лісник F-202 |
| SanitaryFelling_2026_V009 | SanitaryFelling | V-009 | 177.0 | 260.0 | false | ЛК-2026-044 | Лісник F-102 |
| SanitaryFelling_2026_V014 | SanitaryFelling | V-014 | 176.0 | 270.0 | false | ЛК-2026-043 | Фомін О.В. |
| SanitaryFelling_2026_V012 | SanitaryFelling | V-012 | 120.0 | 450.0 | false | ЛК-2026-042 | Фомін О.В. |
| SanitaryFelling_2026_V207 | SanitaryFelling | V-207 | 116.0 | 150.0 | false | ЛК-2026-045 | Лісник F-301 |
| SanitaryFelling_2026_V203 | SanitaryFelling | V-203 | 113.0 | 150.0 | false | ЛК-2026-046 | Лісник F-302 |

**Інтерпретація:** Усі 13 рубок забезпечені лісорубними квитками, однак запит виявляє критичне порушення лісокористування: `MainFelling_2026_V102` (694.0 м³) перевищує як квоту (620.0 м³, +74.0 м³), так і річний приріст виділу V-102 (555.0 м³). Це вимагає коригування плану заготівлі до початку робіт.

### CQ4 — Стиглі хвойні виділи (вік ≥ 81 р.) по лісництвах (`queries/q04_cq4_mature_coniferous.cypher`)

**Результат (10 стиглих хвойних виділів у 4 лісництвах):**

| forestryCode | forestryName | matureCount | totalAreaHa | totalStockM3 | compartments |
|--------------|--------------|------------:|------------:|-------------:|--------------|
| LS-01 | Лісництво «Карпатське» | 4 | 45.7 | 14073.0 | V-002, V-003, V-013, V-014 |
| LS-03 | Лісництво «Верховинське» | 3 | 39.6 | 11704.0 | V-204, V-206, V-208 |
| LS-04 | Лісництво «Дністровське» | 2 | 28.0 | 8344.0 | V-302, V-308 |
| LS-02 | Лісництво «Бескидське» | 1 | 14.3 | 4861.0 | V-102 |

**Інтерпретація:** Найбільший ресурс стиглої хвойної деревини зосереджено в лісництві «Карпатське» (14 073 м³ на 45.7 га) та «Верховинське» (11 704 м³). Водночас два стиглих виділи (`V-014` і `V-302`) вже мають низький NDVI (0.54) і ураження >15 %, тому вони переведені у контур санітарних рубок.

### CQ5 — Перевірка лісовідновлення після рубок (`queries/q05_cq5_reforestation_check.cypher`)

**Результат:** Із 13 рубок 10 мають закріплене весняне садіння 2027 р. (загалом 71 800 саджанців), а **3 рубки головного користування не мають запланованого лісовідновлення**:
1. `MainFelling_2026_V003` (виділ `V-003`, `LS-01`);
2. `MainFelling_2026_V206` (виділ `V-206`, `LS-03`);
3. `MainFelling_2026_V208` (виділ `V-208`, `LS-03`).

**Інтерпретація:** Запит з `OPTIONAL MATCH` і перевіркою `r IS NULL` виконує роль автоматизованого аудиту дотримання екологічних вимог: усі 7 санітарних рубок покриті планами лісовідновлення на 100 %, тоді як 3 рубки головного користування потребують негайного внесення до весняного плану садіння.

### CQ6 — Лісники, відповідальні за виділи із загрозами та пожежним патрулюванням (`queries/q06_cq6_foresters_threats_fire.cypher`)

**Результат (7 лісників із 10 активні у контурах загроз/патрулювання):**

| staffCode | forester | threatCount | threatCompartments | patrolCount | firePatrols |
|-----------|----------|------------:|--------------------|------------:|-------------|
| F-104 | Фомін О.В. | 3 | V-008 (Вітровал), V-012 (Короїд), V-014 (Гниття) | 1 | `FirePatrol_Sept2026_LS01 [2026-09-05]` |
| F-302 | Лісник F-302 | 3 | V-201 (Посуха), V-203 (Короїд), V-204 (Посуха) | 0 | `[]` |
| F-102 | Лісник F-102 | 1 | V-009 (Гниття) | 0 | `[]` |
| F-202 | Лісник F-202 | 1 | V-107 (Короїд) | 1 | `FirePatrol_2026_09_04_LS02 [2026-09-04]` |
| F-301 | Лісник F-301 | 1 | V-207 (Короїд) | 1 | `FirePatrol_2026_09_11_LS03 [2026-09-11]` |
| F-401 | Лісник F-401 | 1 | V-302 (Гниття) | 1 | `FirePatrol_2026_09_16_LS04 [2026-09-16]` |
| F-402 | Лісник F-402 | 1 | V-308 (Вітровал) | 0 | `[]` |

**Інтерпретація:** Найбільше операційне навантаження мають `F-104` (Фомін О.В.: 3 проблемні виділи + пожежний патруль) та `F-302` (3 виділи із загрозами у Верховинському лісництві). Такий розподіл сигналізує про потребу перерозподілу нагляду між менш завантаженими лісниками (`F-101`, `F-201`, `F-203`).

### CQ7 — Недеревна продукція та ліміти збору (`queries/q07_cq7_nontimber_limits.cypher`)

**Результат:**

| product | category | limitValue | unit | compartmentCount | sample compartments |
|---------|----------|-----------:|------|-----------------:|---------------------|
| Білі гриби | Mushrooms | 800.0 | кг/сезон | 22 | V-001, V-005, V-008, V-014, V-101 … |
| Чорниця | Berries | 800.0 | кг/сезон | 8 | V-006, V-008, V-009, V-014, V-104 … |
| Звіробій | MedicinalHerbs | 150.0 | кг/сезон | 6 | V-002, V-005, V-104, V-107, V-203, V-206 |
| Малина лісова | Berries | 500.0 | кг/сезон | 6 | V-004, V-010, V-101, V-201, V-301, V-305 |

**Інтерпретація:** Білі гриби є найпоширенішим недеревним ресурсом (55 % усіх виділів — 22 з 40), причому разом із чорницею вони поділяють спільний ліміт 800 кг/сезон (`Quota_2026_NonTimber_800kg`), що робить цей ліміт ключовим регуляторним вузлом (підтверджується також високим PageRank у Результаті 4).

### CQ8 — Виділи з NDVI < 0.65 для першочергового обстеження (`queries/q08_cq8_low_ndvi_inspection.cypher`)

**Результат (9 виділів):**

| compartment | forestry | ndvi | damagedPct | inspectionPriority | threats |
|-------------|----------|-----:|-----------:|--------------------|---------|
| V-207 | LS-03 | 0.51 | 28.7 | Підтверджена загроза | Короїд-типограф |
| V-203 | LS-03 | 0.53 | 18.4 | Підтверджена загроза | Короїд-типограф |
| V-014 | LS-01 | 0.54 | 19.6 | Підтверджена загроза | Кореневе гниття |
| V-302 | LS-04 | 0.54 | 15.0 | Підтверджена загроза | Кореневе гниття |
| V-012 | LS-01 | 0.60 | 12.0 | Підтверджена загроза | Короїд-типограф |
| V-009 | LS-01 | 0.61 | 15.6 | Підтверджена загроза | Кореневе гниття |
| V-107 | LS-02 | 0.61 | 23.3 | Підтверджена загроза | Короїд-типограф |
| **V-001** | **LS-01** | **0.62** | **6.7** | **Раннє попередження (загрозу ще не ідентифіковано)** | `[]` |
| **V-301** | **LS-04** | **0.63** | **1.6** | **Раннє попередження (загрозу ще не ідентифіковано)** | `[]` |

**Інтерпретація:** Запит виявляє не лише 7 уже відомих уражених виділів, а й 2 приховані аномалії раннього попередження (`V-001` та `V-301`), де частка видимого ураження ще нижча за 10 %, але супутниковий індекс вегетації NDVI вже впав нижче 0.65. Саме ці 2 виділи мають бути першочерговими для польового огляду.

---

## Запити «Аналіз впливу» (C3, глибина ≥ 3)

### CQ9 (Аналіз впливу №1) — Каскадний вплив загрози на процеси, лісовідновлення, виділи й лісництва (`queries/q09_cq9_impact_threat_chain.cypher`)

Запит використовує шлях змінної довжини `[:TRIGGERS|FOLLOWED_BY|APPLIED_TO|PART_OF_FORESTRY*3..4]` і обчислює мінімальну довіру `minPathConfidence` уздовж усього ланцюжка через `reduce()`.

**Результат (7 повних каскадних ланцюжків глибини 4 + 7 ланцюжків глибини 3):**

| threatId | depth 4 chain (Threat → SanitaryFelling → Reforestation → Compartment → Forestry) | minPathConfidence |
|----------|-----------------------------------------------------------------------------------|------------------:|
| `Threat_IpsTypographus` | `Threat_IpsTypographus` → `SanitaryFelling_2026_V012` → `Planting_Spring2027_V012` → `V-012` → `LS-01` | **1.0** |
| `Threat_IpsTypographus_LS02` | `Threat_IpsTypographus_LS02` → `SanitaryFelling_2026_V107` → `Planting_Spring2027_V107` → `V-107` → `LS-02` | 0.8 |
| `Threat_IpsTypographus_LS03` | `Threat_IpsTypographus_LS03` → `SanitaryFelling_2026_V203` → `Planting_Spring2027_V203` → `V-203` → `LS-03` | 0.8 |
| `Threat_IpsTypographus_LS03` | `Threat_IpsTypographus_LS03` → `SanitaryFelling_2026_V207` → `Planting_Spring2027_V207` → `V-207` → `LS-03` | 0.8 |
| `Threat_RootRot_LS01` | `Threat_RootRot_LS01` → `SanitaryFelling_2026_V009` → `Planting_Spring2027_V009` → `V-009` → `LS-01` | 0.8 |
| `Threat_RootRot_LS01` | `Threat_RootRot_LS01` → `SanitaryFelling_2026_V014` → `Planting_Spring2027_V014` → `V-014` → `LS-01` | 0.8 |
| `Threat_RootRot_LS04` | `Threat_RootRot_LS04` → `SanitaryFelling_2026_V302` → `Planting_Spring2027_V302` → `V-302` → `LS-04` | 0.8 |

**Інтерпретація:** Кожна активна біотична загроза запускає 4-рівневий каскад залежностей, що впливає на санітарні рубки, весняні посадки 2027 р. та баланс лісового фонду відповідного лісництва. Наприклад, `Threat_RootRot_LS01` і `Threat_IpsTypographus_LS03` створюють подвійний каскадний тиск на ресурси садіння у `LS-01` та `LS-03`.

### CQ10 (Аналіз впливу №2) — Вплив перевищення квоти (глибина 3+) та `shortestPath` (`queries/q10_cq10_impact_quota_shortest_path.cypher`)

**Частина A (вплив перевищення квоти):**
- `Quota_2026_V102_620m3` (ліміт 620.0 м³) ← `MainFelling_2026_V102` (план 694.0 м³, перевищення +74.0 м³) → квиток `ЛК-2026-047` → виділ `V-102` → лісництво `LS-02` (лісник `F-202`, заплановане садіння `Planting_Spring2027_V102`). Блокування або перегляд квоти `Quota_2026_V102_620m3` безпосередньо впливає на дозвільний документ, графік Бригади №3 та весняне садіння 9200 саджанців.

**Частина B (`shortestPath` від лісника `Forester_F104` до всіх 8 загроз):**

| threatId | hops | Приклад найкоротшого шляху |
|----------|-----:|----------------------------|
| `Threat_IpsTypographus` | 2 | `Forester_F104` ←[:PERFORMED_BY]— `SanitaryFelling_2026_V012` ←[:TRIGGERS]— `Threat_IpsTypographus` |
| `Threat_RootRot_LS01` | 2 | `Forester_F104` ←[:PERFORMED_BY]— `SanitaryFelling_2026_V014` ←[:TRIGGERS]— `Threat_RootRot_LS01` |
| `Threat_Windthrow2026` | 2 | `Forester_F104` —[:SUPERVISES]→ `V-008` —[:AFFECTED_BY]→ `Threat_Windthrow2026` |
| `Threat_IpsTypographus_LS02` | 4 | `Forester_F104` —[:SUPERVISES]→ `V-008` —[:YIELDS_PRODUCT]→ `Product_Blueberries` ←[:YIELDS_PRODUCT]— `V-107` —[:AFFECTED_BY]→ `Threat_IpsTypographus_LS02` |
| `Threat_IpsTypographus_LS03` | 4 | `Forester_F104` —[:SUPERVISES]→ `V-008` —[:YIELDS_PRODUCT]→ `Product_BoletusMushrooms` ←[:YIELDS_PRODUCT]— `V-203` —[:AFFECTED_BY]→ `Threat_IpsTypographus_LS03` |
| `Threat_Drought_LS03` | 4 | `Forester_F104` —[:SUPERVISES]→ `V-008` —[:YIELDS_PRODUCT]→ `Product_BoletusMushrooms` ←[:YIELDS_PRODUCT]— `V-201` —[:AFFECTED_BY]→ `Threat_Drought_LS03` |
| `Threat_RootRot_LS04` | 4 | `Forester_F104` —[:SUPERVISES]→ `V-008` —[:YIELDS_PRODUCT]→ `Product_BoletusMushrooms` ←[:YIELDS_PRODUCT]— `V-302` —[:AFFECTED_BY]→ `Threat_RootRot_LS04` |
| `Threat_Windthrow_LS04` | 5 | `Forester_F104` —[:SUPERVISES]→ `LS-01` ←[:PART_OF_FORESTRY]— `V-003` —[:HAS_DOMINANT_SPECIES]→ `Pinus sylvestris` ←[:HAS_DOMINANT_SPECIES]— `V-308` —[:AFFECTED_BY]→ `Threat_Windthrow_LS04` |

**Інтерпретація:** У межах власного лісництва (`LS-01`) лісник `F-104` знаходиться на відстані 2 кроків від усіх трьох загроз. До загроз інших лісництв найкоротші шляхи (4–5 кроків) проходять через спільні лісові продукти або домінуючі породи — це важлива структурна властивість графа знань, яка пояснює також зв'язність спільнот у Louvain.

---

## Ручна перевірка 3 запитів на малому підграфі (C4)

Для ручної верифікації обрано базовий підграф лісництва **«Карпатське» (`Forestry_LS01`, `origin = 'lab7-8'`)**, який складається з 3 базових виділів (`V-012`, `V-003`, `V-008`) та пов'язаних із ними вузлів:

- `Compartment_V012`: `damagedTreesShare = 12.0`, `standAgeYears = 78`, `ndviValue = 0.60`, порода `Picea abies`, загроза `Threat_IpsTypographus`, процес `SanitaryFelling_2026_V012` (120 м³, квиток `ЛК-2026-042`, квота 450 м³, виконавець `Forester_F104`), продовження `FOLLOWED_BY -> Planting_Spring2027_V012` (5000 саджанців).
- `Compartment_V003`: `damagedTreesShare = 3.5`, `standAgeYears = 105`, `ndviValue = 0.79`, порода `Pinus sylvestris`, загроз немає, процес `MainFelling_2026_V003` (260 м³, квиток `ЛК-2026-039`, квота 300 м³, виконавець `Brigade_01`), зв'язок `FOLLOWED_BY` відсутній.
- `Compartment_V008`: `damagedTreesShare = 1.8`, `standAgeYears = 55`, `ndviValue = 0.82`, порода `Fagus sylvatica`, загроза `Threat_Windthrow2026`, рубок немає.

| Перевірений запит | Покрокове ручне трасування на підграфі `LS-01 (base)` | Результат запиту на підграфі | Збіг |
|-------------------|------------------------------------------------------|------------------------------|:----:|
| **CQ1** (`q01`) | Перевіряємо `damagedTreesShare > 10.0`: `V-012` (12.0 > 10 → так, загроза `Ips typographus`), `V-003` (3.5 → ні), `V-008` (1.8 → ні, хоча має `Windthrow2026`). Очікується рівно 1 виділ: `V-012`. | 1 рядок: `V-012` (`12.0 %`, `Ips typographus`, `confidence=1.0`) | **100 %** |
| **CQ3** (`q03`) | Шукаємо процеси `:TimberHarvesting`: у підграфі їх 2 (`SanitaryFelling_2026_V012` — 120 ≤ 450, квиток `ЛК-2026-042`; `MainFelling_2026_V003` — 260 ≤ 300, квиток `ЛК-2026-039`). Сума = 380.0 м³, перевищень квот = 0. | 2 рядки (`V-003`: 260 м³, `V-012`: 120 м³), `exceedsQuota=false` для обох | **100 %** |
| **CQ5** (`q05`) | Перевіряємо наявність `-[:FOLLOWED_BY]->(:Reforestation)` для обох рубок: `SanitaryFelling_2026_V012` має `Planting_Spring2027_V012` (5000 саджанців); `MainFelling_2026_V003` не має вихідного `FOLLOWED_BY` → `r IS NULL`. | `SanitaryFelling_2026_V012` → Заплановано (5000); `MainFelling_2026_V003` → ВІДСУТНЄ (`null`) | **100 %** |
