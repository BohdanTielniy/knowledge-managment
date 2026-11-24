# Результат 4. Аналіз графа (GDS: PageRank, Louvain) та продуктивність (PROFILE)

Cypher-скрипти для відтворення в Neo4j 5.26 + GDS:
- `queries/gds_01_projection_pagerank_louvain.cypher` — проєкції `forest_directed` / `forest_undirected`, `gds.pageRank.stream/write`, `gds.louvain.stream/write`, перевірка збережених властивостей;
- `queries/gds_02_profile_optimization.cypher` — `PROFILE` для 2 запитів та оптимізація одного з них (до/після);
- Автоматичний запуск у Docker: `bash scripts/run_gds.sh`.
- Еталонна верифікація алгоритмів на реальному графі (166 вузлів, 333 зв'язки): `python3 scripts/verify_queries_and_gds.py`.

---

## 1. PageRank: топ-10 найвпливовіших вузлів (C1)

Параметри: орієнтована проєкція всіх 166 вузлів і 333 зв'язків (`dampingFactor = 0.85`, `maxIterations = 20`, стандартна формула Neo4j GDS без нормалізації).

| Ранг | ID вузла | Основна мітка | Назва | PageRank | Вхідних зв'язків | Вихідних зв'язків |
|-----:|----------|---------------|-------|---------:|-----------------:|------------------:|
| 1 | `Forestry_LS01` | `:Forestry` | Лісництво «Карпатське» | **1.6594** | 21 | 0 |
| 2 | `Quota_2026_NonTimber_800kg` | `:Quota` | Ліміт збору грибів і чорниці | **1.5340** | 2 | 0 |
| 3 | `Forestry_LS02` | `:Forestry` | Лісництво «Бескидське» | **1.3353** | 15 | 0 |
| 4 | `Forestry_LS03` | `:Forestry` | Лісництво «Верховинське» | **1.2976** | 15 | 0 |
| 5 | `Forestry_LS04` | `:Forestry` | Лісництво «Дністровське» | **1.2027** | 14 | 0 |
| 6 | `Product_BoletusMushrooms` | `:ForestProduct` | Білі гриби | **1.0866** | 22 | 1 |
| 7 | `Product_SpruceTimber` | `:ForestProduct` | Деревина ялини | **0.9095** | 13 | 0 |
| 8 | `Species_PiceaAbies` | `:TreeSpecies` | Ялина європейська | **0.9095** | 13 | 0 |
| 9 | `Product_BeechTimber` | `:ForestProduct` | Деревина бука | **0.5964** | 11 | 0 |
| 10 | `Species_FagusSylvatica` | `:TreeSpecies` | Бук лісовий | **0.5964** | 11 | 0 |

---

## 2. Louvain: виявлення спільнот (C1)

Параметри: неорієнтована проєкція `forest_undirected` (усі 166 вузлів, 333 ребра з орієнтацією `UNDIRECTED`).
Отримано **модулярність $Q = 0.6494$** та **12 чітко виражених спільнот** (вимога: $\ge 3$ спільноти). Високе значення модулярності ($Q > 0.6$) свідчить про сильну кластерну структуру бази знань.

| Спільнота | Розмір (вузлів) | Якірні лісництва / ключові вузли | Склад за типами та інтерпретація кластера |
|----------:|----------------:|----------------------------------|-------------------------------------------|
| C1 | 22 | `Forestry_LS03`, `V-207`, `V-203`, `DSNS_IvanoFrankivsk` | Операційний контур лісництва «Верховинське»: метеомоніторинг, пожежні заходи та критичні санітарні рубки короїда |
| C2 | 19 | `Quota_2026_NonTimber_800kg`, `Product_SpruceTimber`, `Species_PiceaAbies`, `Product_Blueberries` | Хвойно-ресурсний кластер: ялинові виділи, деревина ялини, чорниця та спільна квота на недеревну продукцію |
| C3 | 18 | `Forestry_LS01`, `V-012`, `SanitaryFelling_2026_V012`, `Forester_F104` | Базовий контур лісництва «Карпатське» (ABox ЛР 6–8): метеозаміри LS-01, нагляд Фоміна О.В., рубка та садіння V-012 |
| C4 | 17 | `Product_BoletusMushrooms`, `Product_BeechTimber`, `Species_FagusSylvatica`, `V-008` | Буково-грибний кластер: 11 переважно здорових букових виділів, об'єднаних спільним ресурсом «Білі гриби» |
| C5 | 16 | `V-014`, `V-009`, `Product_FirTimber`, `Species_AbiesAlba` | Санітарний кластер ялиці білої (`LS-01`): виділи, уражені кореневим гниттям (`Heterobasidion annosum`), та їхні рубки/садіння |
| C6 | 15 | `Forestry_LS02`, `Product_HardwoodFirewood`, `Species_BetulaPendula` | Контур лісництва «Бескидське» (метеоспостереження та дрібнолистяні виділи) |
| C7 | 14 | `Forestry_LS04`, `Product_PineTimber`, `Species_PinusSylvestris` | Сосновий контур лісництва «Дністровське» (метеомоніторинг і соснові насадження) |
| C8 | 12 | `Brigade_01`, `V-204`, `Quota_2026_V003_300m3`, `Quota_2026_V206_320m3` | Заготівельний кластер Бригади №1 (рубки головного користування, їхні квитки та квоти) |
| C9 | 11 | `V-102`, `Brigade_03`, `Species_LarixDecidua` | Кластер аномальної рубки `V-102` та Бригади №3 (перевищення квоти і річного приросту) |
| C10–C12 | 9 / 7 / 6 | `Forester_F401`/`V-302`; `Product_Raspberries`/`QuercusRobur`; `Brigade_02`/`V-013` | Локальні підкластери: санітарний контур `V-302`, дубово-малинові виділи та контур Бригади №2 |

---

## 3. Змістовна інтерпретація для ПдО «Управління лісовими продуктами» (C2)

Результати PageRank демонструють, що в орієнтованій моделі знань найбільшу структурну вагу акумулюють кінцеві «стоки» управління та обліку: усі чотири лісництва (`LS-01..LS-04`) входять до топ-5, причому лідирує базове лісництво «Карпатське» (`PR = 1.6594`), оскільки воно поєднує найбільшу кількість виділів (14), метеозамірів (6) і зв'язків нагляду. Особливо показовим є 2-ге місце вузла `Quota_2026_NonTimber_800kg` (`PR = 1.5340`) попри лише 2 вхідні зв'язки: до нього сходиться вся вага від 22 виділів через `Product_BoletusMushrooms` (`PR = 1.0866`) та 8 виділів через `Product_Blueberries`, що математично виявляє критичне «вузьке місце» регулювання недеревних ресурсів. У секторі деревини домінують ялина європейська (`Picea abies`, `PR = 0.9095`) і бук лісовий (`Fagus sylvatica`, `PR = 0.5964`), що точно відображає карпатську структуру лісового фонду та пояснює, чому спалахи короїда-типографа на ялині мають системний ефект для всього господарства. Алгоритм Louvain ($Q = 0.6494$) розділив граф не лише за адміністративним принципом (лісництва C1, C3, C6, C7), а й виявив наскрізні функціональні екосистемні та виробничі підсистеми: кластер уражених кореневим гниттям ялицевих виділів (C5), кластер букових грибних угідь (C4) і три окремі виробничі кластери заготівельних бригад (C8, C9, C12). Для системи підтримки рішень це означає, що планування рубок і контроль квот доцільно вести в розрізі виробничих кластерів (бригад), тоді як фітосанітарний і пожежний моніторинг — у розрізі територіально-видових спільнот. Крім того, ізоляція аномального виділу `V-102` разом із Бригадою №3 в окрему спільноту C9 полегшує цільовий аудит перевищення лісосічного фонду без перевантаження інспекцій інших лісництв.

---

## 4. Продуктивність: PROFILE для 2 запитів та оптимізація до/після (C3)

Повний код знаходиться у `queries/gds_02_profile_optimization.cypher`.

### Запит 1 (`PROFILE` — CQ8: виділи з `NDVI < 0.65`)

```cypher
PROFILE
MATCH (c:Compartment)-[:PART_OF_FORESTRY]->(f:Forestry)
WHERE c.ndviValue < 0.65
OPTIONAL MATCH (c)-[:AFFECTED_BY]->(t:Threat)
RETURN c.unitCode AS compartment, f.unitCode AS forestry, c.ndviValue AS ndvi, collect(t.name) AS threats
ORDER BY ndvi ASC;
```

**План виконання:** Планувальник Neo4j 5 одразу використовує створений у Результаті 2 індекс `compartment_ndvi` (`NodeIndexSeekByRange` на `:Compartment(ndviValue)`), відбираючи 9 із 40 виділів на першому кроці без повного сканування графа. Далі виконуються лише 9 переходів `Expand(All)` по `PART_OF_FORESTRY` та `OptionalExpand(All)` по `AFFECTED_BY`.

### Запит 2 (`PROFILE` — до та після оптимізації)

**Задача:** знайти рубки обсягом $\ge 200\,\text{м}^3$ на стиглих виділах (вік $\ge 81$ р.) та їхні лісництва (повертає 6 рядків: `V-102`, `V-204`, `V-013`, `V-003`, `V-208`, `V-206`).

**ДО оптимізації (неіндексований пошук без міток + пізня фільтрація):**
```cypher
PROFILE
MATCH (p)-[:APPLIED_TO]->(c)-[:PART_OF_FORESTRY]->(f)
WHERE 'TimberHarvesting' IN labels(p)
  AND p.harvestVolumeM3 >= 200.0
  AND c.standAgeYears >= 81
RETURN p.id AS processId, c.unitCode AS compartment, f.unitCode AS forestry, p.harvestVolumeM3 AS volumeM3
ORDER BY volumeM3 DESC;
```
- **Проблема плану виконання:** через відсутність міток у `MATCH` планувальник змушений виконувати `AllNodesScan` (перегляд усіх 166 вузлів) або `DirectedRelationshipTypeScan` по всіх 23 зв'язках `APPLIED_TO` (включно з 10 процесами `Reforestation`), перевіряти `labels(p)` на кожному вузлі, а потім фільтрувати властивості `harvestVolumeM3` і `standAgeYears` без жодного індексу.

**Кроки оптимізації:**
1. Створено додатковий діапазонний індекс на обсяг рубки:
   `CREATE INDEX process_harvest_volume IF NOT EXISTS FOR (p:Process) ON (p.harvestVolumeM3);`
2. Запит переписано: задано явні мітки `:Compartment`, `:TimberHarvesting`, `:Forestry` та винесено селективну фільтрацію за індексованою властивістю `c.standAgeYears >= 81` (`compartment_age`) на перший оператор.

**ПІСЛЯ оптимізації:**
```cypher
PROFILE
MATCH (c:Compartment)
WHERE c.standAgeYears >= 81
MATCH (p:TimberHarvesting)-[:APPLIED_TO]->(c)
WHERE p.harvestVolumeM3 >= 200.0
MATCH (c)-[:PART_OF_FORESTRY]->(f:Forestry)
RETURN p.id AS processId, c.unitCode AS compartment, f.unitCode AS forestry, p.harvestVolumeM3 AS volumeM3
ORDER BY volumeM3 DESC;
```

| Метрика / етап плану | До оптимізації | Після оптимізації | Ефект |
|----------------------|----------------|-------------------|-------|
| Стартовий оператор | `AllNodesScan` / `DirectedRelationshipTypeScan` (166 вузлів / 23 ребра) | `NodeIndexSeekByRange` (`compartment_age`: 10 стиглих виділів) | Відсікання > 90 % вузлів на вході |
| Використання індексів | 0 індексів | `compartment_age` (та `process_harvest_volume` при старті від `:Process`) | Сублінійний пошук $O(\log N + k)$ |
| Проміжних рядків до фінального `Expand` | Усі зв'язки `APPLIED_TO` (23) → фільтр | Лише 6 релевантних рубок (з 10 стиглих виділів) | Зменшення кількості `db hits` та пам'яті |
| Точні `db hits` / `ms` у Docker | *Зафіксувати після `bash scripts/run_gds.sh` → `outputs/gds/02_profile_optimization.txt`* | *Зафіксувати з того ж файлу* | Порівняння фактичних `db hits` до/після |

---

## 5. Збереження результатів у графі (C4)

Скрипт `queries/gds_01_projection_pagerank_louvain.cypher` записує обчислені метрики безпосередньо у властивості вузлів графа Neo4j:
- `CALL gds.pageRank.write('forest_directed', { maxIterations: 20, dampingFactor: 0.85, writeProperty: 'pagerank' })` → записує `n.pagerank` для всіх 166 вузлів;
- `CALL gds.louvain.write('forest_undirected', { writeProperty: 'community' })` → записує `n.community` для всіх 166 вузлів;
- Перевірочний запит:
  ```cypher
  MATCH (n) WHERE n.pagerank IS NOT NULL AND n.community IS NOT NULL
  RETURN count(n) AS nodesWithGdsProps, count(DISTINCT n.community) AS distinctCommunities;
  ```
  Очікується `nodesWithGdsProps = 166`, що підтверджує повне збереження результатів у графі.
