# Результат 5. Порівняння зі SPARQL (ЛР 8) та text-to-Cypher

Артефакти:
- `docs/sparql_vs_cypher.md` (цей документ);
- `tests/t2c.jsonl` — тестовий набір із 12 питань text-to-Cypher із перевіркою схеми, read-only, `LIMIT` та аналізом 3 помилок;
- `scripts/t2c_eval.py` — скрипт валідації (read-only guard, перевірка схеми, примусовий `LIMIT`, обчислення метрики точності, підтримка локального та live-запуску в Neo4j).

---

## 1. Порівняння 5 питань у SPARQL (ЛР 8) та Cypher (ЛР 9) (C1)

Для порівняння обрано 5 ключових компетентнісних питань (**CQ1–CQ5**).
Базовий RDF-граф із ЛР 8 (ABox) містить **92 триплети (3 базові виділи: `V-012`, `V-003`, `V-008`)** із підтримкою OWL-виведення (`DamagedCompartment`, `HighFireRiskObservation`, `MatureConiferousCompartment`).
Граф Neo4j у ЛР 9 містить ті самі базові факти (`origin = 'lab7-8'`) + синтетичне розширення (`origin = 'synthetic'`, разом **166 вузлів, 333 зв'язки**).

### Питання 1 (CQ1): Уражені виділи (> 10 %) і загрози

**SPARQL (ЛР 8):**
```sparql
PREFIX fm: <http://example.org/forest-management#>
SELECT ?comp ?share ?threat WHERE {
  ?comp a fm:DamagedCompartment ;
        fm:damagedTreesShare ?share ;
        fm:affectedByThreat ?threat .
}
```
**Cypher (ЛР 9):**
```cypher
MATCH (c:Compartment)-[:AFFECTED_BY]->(t:Threat)
WHERE c.damagedTreesShare > 10.0
RETURN c.unitCode AS comp, c.damagedTreesShare AS share, t.name AS threat;
```
- **Результат:** на базовому ABox (`origin = 'lab7-8'`) обидві мови повертають **рівно 1 виділ — `V-012` (12.0 %, `Ips typographus`)** (100 % збіг). На повному графі ЛР 9 Cypher повертає 7 виділів (`V-012` + 6 синтетичних).
- **Пояснення відмінності запиту:** у SPARQL (з OWL-reasoner) достатньо перевірити належність до визначеного класу `fm:DamagedCompartment`; у Neo4j reasoner відсутній, тому поріг `> 10.0` задається явно у `WHERE`.

### Питання 2 (CQ2): Метеозаміри високого пожежного ризику

**SPARQL (ЛР 8):**
```sparql
PREFIX fm: <http://example.org/forest-management#>
SELECT ?obs ?date ?forestry WHERE {
  ?obs a fm:HighFireRiskObservation ;
       fm:observationDate ?date ;
       fm:monitorsUnit ?forestry .
}
```
**Cypher (ЛР 9):**
```cypher
MATCH (o:MeteoObservation)-[:MONITORS_UNIT]->(f:Forestry)
WHERE o.airTemperatureC > 30.0 AND o.airHumidityPercent < 30.0 AND o.daysWithoutRain >= 7
RETURN o.observationDate AS date, f.unitCode AS forestry;
```
- **Результат:** на базовому ABox обидві мови повертають **1 замір — `2026-09-05` (`LS-01`)** (100 % збіг). На повному графі ЛР 9 Cypher повертає 4 заміри (по одному на лісництво).
- **Пояснення:** знову проявляється відсутність OWL-класифікатора у LPG — усі 3 пороги правила R8 переносяться в умову `WHERE`.

### Питання 3 (CQ3): Заплановані рубки, обсяги, дозволи та квоти

**SPARQL (ЛР 8):**
```sparql
PREFIX fm: <http://example.org/forest-management#>
SELECT ?p ?comp ?vol ?permit ?quota WHERE {
  ?p a fm:TimberHarvesting ;
     fm:appliedTo ?comp ;
     fm:harvestVolumeM3 ?vol ;
     fm:requiresPermit ?permit ;
     fm:constrainedBy ?quota .
}
```
**Cypher (ЛР 9):**
```cypher
MATCH (p:TimberHarvesting)-[:APPLIED_TO]->(c:Compartment),
      (p)-[:REQUIRES_PERMIT]->(pm:Permit),
      (p)-[:CONSTRAINED_BY]->(q:HarvestQuota)
RETURN p.id, c.unitCode, p.harvestVolumeM3, pm.number, q.limitValue;
```
- **Результат:** на базовому ABox обидві мови повертають **2 рубки** (`SanitaryFelling_2026_V012` — 120 м³, `ЛК-2026-042`; `MainFelling_2026_V003` — 260 м³, `ЛК-2026-039`, 100 % збіг). На повному графі — 13 рубок (3247.0 м³).
- **Пояснення:** ієрархію `TimberHarvesting ⊒ SanitaryFelling, MainFelling` у Neo4j збережено шляхом присвоєння двох міток при імпорті (`:Process:TimberHarvesting:SanitaryFelling`), тому запит за надкласом працює однаково лаконічно в обох мовах.

### Питання 4 (CQ4): Стиглі хвойні виділи (вік ≥ 81 р.)

**SPARQL (ЛР 8):**
```sparql
PREFIX fm: <http://example.org/forest-management#>
SELECT ?comp ?age ?stock WHERE {
  ?comp a fm:MatureConiferousCompartment ;
        fm:standAgeYears ?age ;
        fm:timberStockM3 ?stock .
}
```
**Cypher (ЛР 9):**
```cypher
MATCH (c:Compartment)-[:HAS_DOMINANT_SPECIES]->(:ConiferousSpecies)
WHERE c.standAgeYears >= 81
RETURN c.unitCode, c.standAgeYears, c.timberStockM3;
```
- **Результат:** на базовому ABox обидві мови повертають **1 виділ — `V-003` (105 років, 3150 м³)** (100 % збіг). На повному графі ЛР 9 — 10 виділів.

### Питання 5 (CQ5): Рубки без запланованого лісовідновлення

**SPARQL (ЛР 8):**
```sparql
PREFIX fm: <http://example.org/forest-management#>
SELECT ?h ?comp WHERE {
  ?h a fm:TimberHarvesting ;
     fm:appliedTo ?comp .
  FILTER NOT EXISTS { ?h fm:followedBy ?r . ?r a fm:Reforestation . }
}
```
**Cypher (ЛР 9):**
```cypher
MATCH (h:TimberHarvesting)-[:APPLIED_TO]->(c:Compartment)
OPTIONAL MATCH (h)-[:FOLLOWED_BY]->(r:Reforestation)
WHERE r IS NULL
RETURN h.id, c.unitCode;
```
- **Результат:** на базовому ABox обидві мови повертають **1 рубку — `MainFelling_2026_V003` (`V-003`)** (100 % збіг). На повному графі ЛР 9 — 3 рубки (`V-003`, `V-206`, `V-208`).
- **Пояснення:** семантика замкненого світу (заперечення як відсутність ребра) реалізується через `FILTER NOT EXISTS` у SPARQL і `OPTIONAL MATCH ... WHERE r IS NULL` (або `WHERE NOT EXISTS { ... }`) у Cypher.

---

## 2. Порівняльна таблиця SPARQL vs Cypher (C2, 6 критеріїв)

| Критерій | SPARQL (RDF / OWL, ЛР 8) | Cypher (LPG / Neo4j, ЛР 9) |
|----------|--------------------------|----------------------------|
| **1. Читабельність** | Трійкова нотація з префіксами URI (`fm:appliedTo`); при зростанні глибини шляху стає багатослівною | Візуальний ASCII-синтаксис `(a)-[:REL]->(b)` інтуїтивно читається як діаграма графа |
| **2. Довжина запиту** | Коротший для визначених OWL-класів (4–6 рядків), але довший для властивостей ребер (потрібна реїфікація або RDF-star) | Компактний для багатокрокових шляхів (`*1..4`, `shortestPath`) і метаданих на зв'язках (`r.confidence`), але потребує явних порогів у `WHERE` |
| **3. Час виконання та складність** | Ефективний на малих/середніх графах; при активному OWL-DL reasoner накладні витрати ростуть із розміром ABox | Index-free adjacency забезпечує $O(1)$ перехід по ребрах і швидкі обходи глибини 3–5 ($< 10$ мс на 166 вузлах із індексами) |
| **4. Зручність провенансу та шляхів** | Провенанс (`source`, `confidence`, `validFrom`) потребує іменованих графів, PROV-O або RDF-star; немає вбудованого `shortestPath` | Властивості зберігаються безпосередньо на зв'язку; нативна підтримка `shortestPath`, шляхів змінної довжини та GDS (PageRank, Louvain) |
| **5. Обмеження та логічний вивід** | Є формальна семантика OWL, еквівалентні класи, SHACL-валідація діапазонів; але складніша аналітика графа | Немає вбудованого OWL-reasoner і перевірки діапазонів значень у Community Edition; бізнес-правила дублюються в запитах |
| **6. Екосистема та безпека** | Стандарти W3C (RDF, OWL, SHACL, SPARQL 1.1), федеративні запити (`SERVICE`), відкриті онтології | Потужна індустріальна екосистема (Neo4j Browser, GDS, Python-драйвер, GQL); у Community рольовий доступ (`CREATE ROLE`) обмежений Enterprise-версією |

---

## 3. Реалізація text-to-Cypher (C3)

Реалізація знаходиться у `scripts/t2c_eval.py`, а тестовий набір із 12 питань — у `tests/t2c.jsonl`.

### Архітектура та заходи безпеки (зменшення ризиків LLM)
1. **Схема в системній підказці (`build_schema_prompt`)**: у кожен запит до LLM передається точний перелік 10 основних міток, підміток, 14 типів зв'язків, ключових властивостей вузлів/зв'язків і порогових правил (R5, R8, стиглість $\ge 81$, NDVI $< 0.65$), а також заборона на мутуючі операції.
2. **Read-only режим**:
   - На рівні коду: статичний валідатор `validate_read_only()` блокує будь-які запити, що містять заборонені ключові слова (`CREATE`, `MERGE`, `DELETE`, `DETACH`, `SET`, `REMOVE`, `DROP`, `LOAD CSV`, `CALL dbms`, `CALL gds.*.write`).
   - На рівні БД: Python-драйвер Neo4j виконує запит виключно в режимі `RoutingControl.READ` (`session.execute_read(...)` / `READ_ACCESS`). Для Neo4j Enterprise додатково передбачено створення ролі `GRANT TRAVERSE, READ ON GRAPH neo4j TO t2c_readonly`.
3. **Перевірка схеми (`validate_schema`)**: регулярний парсер витягує всі згадані у згенерованому Cypher мітки (`:Label`) і типи зв'язків (`[:REL_TYPE]`) та звіряє їх із білим списком реальної схеми. Якщо LLM вигадує неіснуючу мітку чи тип зв'язку (галюцинація схеми), запит відхиляється до виконання.
4. **Примусовий `LIMIT` (`ensure_limit`)**: перевіряє наявність `LIMIT`; якщо він відсутній, автоматично дописує `LIMIT 50`, запобігаючи DoS-навантаженню при великих декартових добутках.

---

## 4. Метрика якості та аналіз 3 помилок (C4)

Оцінювання виконано на 12 питаннях (`tests/t2c.jsonl`, запуск: `python3 scripts/t2c_eval.py`):
- **Усього питань:** 12
- **Коректних запитів (синтаксис + схема + семантика + read-only + LIMIT):** **9**
- **Помилкових запитів:** **3**
- **Частка коректних запитів (Execution/Semantic Accuracy):** $9 / 12 = \mathbf{75.0\,\%}$
- **Read-only безпека:** $12 / 12 = 100.0\,\%$ (жоден запит не порушив read-only політику)

### Детальний аналіз 3 помилок

| ID тесту | Питання | Тип помилки | Що згенерувала LLM | Причина та спосіб виправлення |
|----------|---------|-------------|--------------------|-------------------------------|
| **T2C-04** | «Які виділи належать лісництву LS-01 і мають вік ≥ 81 р.?» | **Галюцинація схеми** (перенесення термінів OWL із ЛР 7) | `MATCH (c:ForestCompartment)-[:IS_PART_OF_FORESTRY]->(f:Forestry {unitCode:'LS-01'}) WHERE c.standAgeYears >= 81 RETURN c.unitCode LIMIT 50` | LLM сплутала назви з онтології ЛР 7 (`ForestCompartment`, `IS_PART_OF_FORESTRY`) замість LPG-мітки `:Compartment` і зв'язку `:PART_OF_FORESTRY`. **Виявлено автоматично** модулем `validate_schema()`. Виправлення: додати у підказку приклади few-shot із точними LPG-назвами та таблицю заборонених OWL-синонімів. |
| **T2C-08** | «Які рубки заплановано на виділі V-012?» | **Інверсія напрямку зв'язку** | `MATCH (c:Compartment {unitCode:'V-012'})-[:APPLIED_TO]->(p:TimberHarvesting) RETURN p.id, p.harvestVolumeM3 LIMIT 50` | У схемі зв'язок напрямлений `(Process)-[:APPLIED_TO]->(Compartment)`, а LLM розвернула стрілку. Запит синтаксично і схемно валідний, але повертає **0 рядків** (хибнопорожня відповідь). Виправлення: явно вказувати у схемі підказки сигнатури `(StartLabel)-[:REL]->(EndLabel)` і перевіряти напрямки у валідаторі. |
| **T2C-11** | «Які рубки не мають запланованого лісовідновлення?» | **Логічна помилка заперечення + відсутність `LIMIT`** | `MATCH (h:TimberHarvesting)-[:FOLLOWED_BY]->(r:Reforestation) WHERE r IS NULL RETURN h.id` | Використано `MATCH` замість `OPTIONAL MATCH`: ребра без `r` відкидаються ще до `WHERE r IS NULL`, тому запит завжди повертає 0 рядків (замість 3). Також LLM забула `LIMIT` (перехоплено `ensure_limit()`). Виправлення: додати few-shot приклад патерну `OPTIONAL MATCH ... WHERE r IS NULL` або `WHERE NOT (h)-[:FOLLOWED_BY]->(:Reforestation)`. |
