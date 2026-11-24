#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo "[1/3] Демо RAG-конвеєра (Результат 1)"
python3 src/rag.py
echo "[2/3] Автотести REST API та експорт OpenAPI (Результат 3)"
python3 scripts/test_api.py
echo "[3/3] Оцінювання Graph vs Text, 32 тестів і оптимізації до/після (Результати 2, 4, 5)"
python3 src/eval_rag.py
echo "Усі етапи ЛР 11 виконано успішно!"
