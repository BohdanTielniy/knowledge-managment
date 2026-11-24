#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
: "${NEO4J_PASSWORD:?Задайте NEO4J_PASSWORD у .env}"
C=lab09-neo4j
mkdir -p outputs/gds

echo "=== [1/2] GDS PageRank + Louvain ==="
docker exec -i "$C" cypher-shell -u neo4j -p "$NEO4J_PASSWORD" --format verbose < queries/gds_01_projection_pagerank_louvain.cypher | tee outputs/gds/01_pagerank_louvain.txt

echo "=== [2/2] PROFILE та оптимізація ==="
docker exec -i "$C" cypher-shell -u neo4j -p "$NEO4J_PASSWORD" --format verbose < queries/gds_02_profile_optimization.cypher | tee outputs/gds/02_profile_optimization.txt

echo "Результати Результату 4 збережено в outputs/gds/"
