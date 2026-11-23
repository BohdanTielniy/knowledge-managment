#!/usr/bin/env bash
set -u
cd "$(dirname "$0")/.."
[ -f .env ] && set -a && . ./.env && set +a
: "${NEO4J_PASSWORD:?Задайте NEO4J_PASSWORD у .env}"
C=lab09-neo4j
mkdir -p outputs
cs() { docker exec -i "$C" cypher-shell -u neo4j -p "$NEO4J_PASSWORD" --format verbose "$@"; }

echo "[1/6] Очікування готовності Neo4j..."
for i in $(seq 1 60); do
  docker exec "$C" cypher-shell -u neo4j -p "$NEO4J_PASSWORD" "RETURN 1" >/dev/null 2>&1 && break
  sleep 3
done

echo "[2/6] Обмеження та індекси"
cs < import/00_constraints_indexes.cypher | tee outputs/00_constraints_indexes.txt

echo "[3/6] Перший імпорт"
cs < import/01_import_nodes.cypher | tee outputs/01_import_nodes.txt
cs < import/02_import_rels.cypher  | tee outputs/02_import_rels.txt
cs < import/03_verify_counts.cypher | tee outputs/03_counts_after_first_import.txt

echo "[4/6] Повторний імпорт (перевірка ідемпотентності)"
cs < import/01_import_nodes.cypher > outputs/05_reimport_nodes.txt
cs < import/02_import_rels.cypher  > outputs/05_reimport_rels.txt
cs < import/03_verify_counts.cypher | tee outputs/03_counts_after_second_import.txt

echo "[5/6] Порівняння кількостей до/після (рядки з часом виконання ігноруються)"
strip() { grep -v "ready to start consuming query" "$1"; }
if diff -q <(strip outputs/03_counts_after_first_import.txt) <(strip outputs/03_counts_after_second_import.txt) >/dev/null; then
  echo "OK: кількості збігаються — імпорт ідемпотентний" | tee outputs/06_idempotency.txt
else
  echo "УВАГА: кількості відрізняються!" | tee outputs/06_idempotency.txt
  diff <(strip outputs/03_counts_after_first_import.txt) <(strip outputs/03_counts_after_second_import.txt) | tee -a outputs/06_idempotency.txt
fi

echo "[6/6] Порушення обмежень (очікується помилка)"
cs < import/04a_violation_id.cypher       2>&1 | tee outputs/07a_violation_id.txt
cs < import/04b_violation_unitcode.cypher 2>&1 | tee outputs/07b_violation_unitcode.txt
echo "Готово. Результати: outputs/"
