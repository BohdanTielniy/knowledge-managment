#!/usr/bin/env bash
set -euo pipefail
python3 etl/load.py
python3 src/olap_runner.py
python3 src/semantic_layer.py
python3 src/text_to_sql.py
python3 dashboard/build_dashboard.py
echo "Lab 12 pipeline completed successfully."
