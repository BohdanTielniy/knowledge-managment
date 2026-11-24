#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
: "${NEO4J_PASSWORD:?Задайте NEO4J_PASSWORD у .env}"
C=lab09-neo4j
mkdir -p outputs/queries

for q in queries/q*.cypher; do
  base=$(basename "$q" .cypher)
  echo "=== Виконання $q ==="
  docker exec -i "$C" cypher-shell -u neo4j -p "$NEO4J_PASSWORD" --format verbose < "$q" | tee "outputs/queries/${base}.txt"
done
echo "Усі запити Результату 3 збережено в outputs/queries/"
