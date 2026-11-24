#!/usr/bin/env bash
set -euo pipefail
python3 src/build_gold_dataset.py
python3 src/extract_rules.py
python3 src/extract_llm.py
python3 src/eval_extraction.py
python3 src/graph_and_patterns.py
echo "Lab 13 pipeline completed successfully."
