#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=.
python3 reco/eval.py
python3 reco/explain.py
python3 app/demo_cli.py
echo "Lab 16 full pipeline completed successfully."
