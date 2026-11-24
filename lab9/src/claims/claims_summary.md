# Підсумок верифікації тверджень (Протокол «LLM-експерт», п. 6)

Зведена статистика за `claims/claims.csv`:

| Показник | Значення |
|----------|----------|
| Усього тверджень | 14 (`C001`–`C014`) |
| Підтверджено (`verified`) | **11** (**78.6 %** від усіх, **84.6 %** від перевірених) |
| Відхилено (`rejected`) | **2** (`C013`, `C014` — **14.3 %**) |
| Очікує локального підтвердження в Docker (`pending`) | **1** (`C006` — версія GDS у контейнері — **7.1 %**) |

## Відхилені твердження (з поясненням)
1. **`C013` (рівень V4, `rejected`):** пропозиція LLM у `T2C-04` використати назви з OWL-онтології ЛР 7 (`:ForestCompartment`, `[:IS_PART_OF_FORESTRY]`). Відхилено автоматичним валідатором схеми `validate_schema()` у `scripts/t2c_eval.py`, оскільки в LPG-схемі використовуються `:Compartment` і `[:PART_OF_FORESTRY]`.
2. **`C014` (рівень V4, `rejected`):** пропозиція LLM у `T2C-11` шукати рубки без лісовідновлення через `MATCH (h)-[:FOLLOWED_BY]->(r) WHERE r IS NULL`. Відхилено, бо внутрішнє з'єднання `MATCH` відкидає відсутні зв'язки ще до `WHERE`, повертаючи 0 рядків замість 3; коректний патерн — `OPTIONAL MATCH ... WHERE r IS NULL`.

## Перелік джерел
1. Звіти та онтологія/ABox попередніх робіт: ЛР 6–8 (тема «Управління лісовими продуктами»).
2. Лекція 9 курсу «Сховища знань та управління знаннями» (ЛНУ ім. Івана Франка, 2026–2027 н. р.).
3. Robinson, I., Webber, J., & Eifrem, E. (2015). *Graph Databases: New Opportunities for Connected Data* (2nd ed.). O'Reilly Media.
4. Francis, N. et al. (2018). *Cypher: An Evolving Query Language for Property Graphs*. Proceedings of SIGMOD 2018.
5. Neo4j Cypher Manual (v5.x): Constraints, Indexes, MERGE, Execution Plans & PROFILE.
6. Neo4j Graph Data Science (GDS) Manual (v2.x): PageRank, Louvain, Graph Projections.
7. Neo4j Operations Manual (v5.x): Authentication, Authorization, Docker Deployment.
8. Програмні верифікатори репозиторію: `scripts/check_data.py`, `scripts/verify_queries_and_gds.py`, `scripts/t2c_eval.py`.
