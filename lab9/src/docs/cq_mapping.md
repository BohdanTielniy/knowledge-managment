# Відображення компетентнісних питань (CQ) на шаблони Cypher-шляхів

CQ1–CQ8 — це питання KQ1–KQ8 із ЛР 7 (нумерація збережена). Схема графа: `docs/graph_schema.png`.
У шаблонах показано лише шляхи й умови; повні запити з результатами та інтерпретацією — у `queries/*.cypher` та `docs/cypher_results.md` (Результат 3).

Позначення: `[:T]` — зв'язок типу `T` із властивостями походження `source`, `confidence`, `validFrom`; `|` у мітках — «або» (Neo4j 5 label expressions).

| CQ | Питання (скорочено) | Шаблон шляху / умови | Походження |
|----|---------------------|----------------------|------------|
| CQ1 | Які виділи уражені (>10 %) і якою загрозою | `(c:Compartment)-[:PART_OF_FORESTRY]->(f:Forestry)`, `(c)-[:HAS_DOMINANT_SPECIES]->(s:TreeSpecies)`, `(c)-[:AFFECTED_BY]->(t:Threat)`; `WHERE c.damagedTreesShare > 10.0` | `AFFECTED_BY.source/confidence` |
| CQ2 | Які метеозаміри означають високий пожежний ризик і в яких лісництвах | `(o:MeteoObservation)-[:MONITORS_UNIT]->(f:Forestry)`, `OPTIONAL MATCH (a:Forester)-[:SUPERVISES]->(f)`; `WHERE o.airTemperatureC > 30 AND o.airHumidityPercent < 30 AND o.daysWithoutRain >= 7` | `MONITORS_UNIT.validFrom` = дата заміру |
| CQ3 | Які рубки заплановані, який обсяг і за яким квитком | `(p:TimberHarvesting)-[:APPLIED_TO]->(c:Compartment)`, `(p)-[:REQUIRES_PERMIT]->(pm:Permit)`, `(p)-[:PERFORMED_BY]->(a:Actor)`, `(p)-[:CONSTRAINED_BY]->(q:HarvestQuota)` | `REQUIRES_PERMIT.source` |
| CQ4 | Які виділи — стиглі хвойні (≥ 81 р.) і їхні показники | `(c:Compartment)-[:HAS_DOMINANT_SPECIES]->(s:ConiferousSpecies)`; `WHERE c.standAgeYears >= 81` | `HAS_DOMINANT_SPECIES.confidence` |
| CQ5 | Яке лісовідновлення закріплене за ділянками після рубок | `(h:TimberHarvesting)-[:FOLLOWED_BY]->(r:Reforestation)-[:APPLIED_TO]->(c:Compartment)`; відсутність — `OPTIONAL MATCH` + `WHERE r IS NULL` | `FOLLOWED_BY.validFrom` |
| CQ6 | Які лісники відповідають за виділи з загрозами/пожежним ризиком | `(a:Forester)-[:SUPERVISES]->(c:Compartment)-[:AFFECTED_BY]->(t:Threat)` та `(o:MeteoObservation)-[:TRIGGERS]->(:FirePreventionMeasure)-[:PERFORMED_BY]->(a)` | `SUPERVISES.source` |
| CQ7 | Які виділи дають недеревну продукцію і які ліміти збору | `(c:Compartment)-[:YIELDS_PRODUCT]->(p:NonTimberProduct)-[:LIMITED_BY]->(q:NonTimberCollectionLimit)` | `YIELDS_PRODUCT.confidence` |
| CQ8 | Які ділянки мають NDVI < 0.65 (першочергове обстеження) | `(c:Compartment)`; `WHERE c.ndviValue < 0.65`; контекст: `(c)-[:PART_OF_FORESTRY]->(f)`, `OPTIONAL MATCH (c)-[:AFFECTED_BY]->(t)` | — |
| CQ9 (вплив) | Які залежності виникають від загрози на глибину ≥ 3 | `(t:Threat)-[:AFFECTED_BY*1..]-(c)`, `(t)-[:TRIGGERS]->(p:Process)-[:APPLIED_TO\|REQUIRES_PERMIT\|CONSTRAINED_BY\|FOLLOWED_BY*1..3]->(x)` | мінімум `confidence` на шляху |
| CQ10 (вплив) | Що зачепить зміна квоти/квитка: які процеси, виділи, лісництва | `(q:Quota)<-[:CONSTRAINED_BY]-(p:Process)-[:APPLIED_TO]->(c)-[:PART_OF_FORESTRY]->(f)` + `shortestPath` між `Forester` і `Threat` | `source` кожного зв'язку на шляху |

CQ9 і CQ10 — додаткові питання для двох запитів «аналіз впливу» (Результат 3, крок 3).

## Властивості походження на зв'язках (крок 3)

| Властивість | Тип | Значення |
|-------------|-----|----------|
| `source` | string | `lab7-8-abox` — факт із ЛР 6–8; `synthetic-gen-seed42` — згенерований `scripts/gen_data.py` |
| `confidence` | float 0–1 | `1.0` — явно заданий у ЛР 6–8; `0.8` — синтетичний. Це умовна шкала довіри до джерела, а не статистична ймовірність |
| `validFrom` | date | Дата початку чинності: дата заміру, запланованої рубки тощо; для структурних фактів — `2026-09-01` (початок змодельованого сценарію) |

Запит для перевірки походження: `MATCH ()-[r]->() RETURN r.source, r.confidence, count(*)`.

## Порівняння зі схемою онтології ЛР 6–7 (крок 4)

| Конструкція онтології (OWL, ЛР 6–7) | У графі Neo4j | Коментар |
|-------------------------------------|---------------|----------|
| Клас верхнього рівня (`ForestCompartment`, `Forestry`, `ForestThreat`, `ForestActor` …) | Основна мітка (`:Compartment`, `:Forestry`, `:Threat`, `:Actor`) | 6 надкласів і 3 рівні підкласів згорнуто до 10 міток |
| Підклас (`SanitaryFelling`, `Forester`, `InsectPest`, `ConiferousSpecies` …) | Додаткова мітка на тому ж вузлі (`:Process:TimberHarvesting:SanitaryFelling`) | 19 додаткових міток; ієрархію `TimberHarvesting ⊒ SanitaryFelling, MainFelling` збережено через дві мітки |
| Визначений клас (`DamagedCompartment`, `MatureConiferousCompartment`, `HighFireRiskObservation`) | **Не зберігається**; обчислюється запитом за порогами (CQ1, CQ4, CQ2) | У LPG немає reasoner-а; клас можна матеріалізувати міткою через `SET`, але тоді результат застарілий після змін даних |
| Object property (`isPartOfForestry`, `affectedByThreat`, …; 13 шт.) | Тип зв'язку (`PART_OF_FORESTRY`, `AFFECTED_BY`, …; 14 шт.) | Додано `LIMITED_BY` (ліміти збору недеревної продукції), який в ЛР 6 не мав окремого предиката |
| Data property (`fm:damagedTreesShare`, `fm:ndviValue` …; 16–17 шт.) | Властивість вузла | Типи XSD → типи Neo4j (`xsd:decimal` → Float, `xsd:integer` → Integer, `xsd:date` → Date) |
| `owl:inverseOf` (`hasCompartment`, `monitorsUnit`, `supervisedByForester` …) | Не зберігається; зв'язок читається в зворотному напрямку | Один зв'язок замість пари |
| `owl:TransitiveProperty` (`isPartOfForestry`) | Шлях змінної довжини `[:PART_OF_FORESTRY*]` | Виводиться запитом, а не reasoner-ом |
| `FunctionalProperty`, `AsymmetricProperty`, `owl:disjointWith` | Native-обмежень немає | Унікальність id/unitCode — обмеженнями; функціональність і неперетинність — перевірочними запитами |
| Іменовані графи (`taxation`, `meteo`, `management`) | Властивості `origin`, `source` | Поділ за походженням, а не за темою |
| Провенанс (PROV-O, окремі трійки) | Властивості на зв'язку (`source`, `confidence`, `validFrom`) | Перевага LPG: метадані прямо на зв'язку, без реїфікації |
| SHACL-форми (ЛР 8) | Унікальні обмеження + індекси; діапазони значень не перевіряються | У Community немає обмежень типу/діапазону властивості |
| `owl:equivalentClass` з числовими фасетами | Умови `WHERE` у запитах | Пороги R5, R8 тепер у коді запитів, а не в схемі |
