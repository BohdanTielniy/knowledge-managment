# СР 9. Критерії порівняння графових баз (Neo4j, Memgraph, GraphDB Free)

Бенчмарк на датасеті ПдО «Управління лісовими продуктами» (**668 вузлів, 1529 зв’язків**, `seed = 42`) та 5 еквівалентних запитах (Cypher для Neo4j і Memgraph, SPARQL 1.1 для GraphDB Free).

## Запуск у Docker (2 команди)

```bash
cd sr09

# 1. Підняти всі 3 графові бази (Neo4j 5.26, Memgraph, GraphDB 10.8 Free)
docker compose up -d neo4j memgraph graphdb

# 2. Запустити бенчмарк (чекає готовності баз, завантажує дані, виконує 5 запитів × 5 прогонів)
docker compose run --rm bench

# Після завершення зупинити контейнери:
docker compose down
```

Результати зберігаються в `outputs/benchmark_results.json` та `outputs/benchmark_summary.txt`.
