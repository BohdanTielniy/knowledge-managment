#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
BACKEND="${BACKEND:-neural}"
mkdir -p outputs

echo "============================================================"
echo "ЛР 10: повний прогін (BACKEND=${BACKEND}, seed=42)"
echo "============================================================"

echo "[1/5] Підготовка корпусу та очищення (Результат 1)"
python3 src/prepare_corpus.py

echo "[2/5] Порівняння 3 стратегій chunking (Результат 2)"
python3 src/chunking.py --backend "${BACKEND}"

echo "[3/5] Векторний індекс HNSW + 2 моделі + upsert/delete (Результат 3)"
python3 src/index.py --backend "${BACKEND}"

echo "[4/5] Гібридний пошук BM25 + Dense + RRF + Rerank + pre-filter (Результат 4)"
python3 src/hybrid.py --backend "${BACKEND}"

echo "[5/5] Оцінювання 4 конфігурацій на золотому наборі + Cohen's kappa (Результат 5)"
python3 src/eval_metrics.py --backend "${BACKEND}"

echo "Готово! Усі результати збережено в outputs/ та docs/."
