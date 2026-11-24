#!/usr/bin/env bash
set -euo pipefail
python3 quality/profile_baseline.py
python3 quality/dedup.py
python3 quality/ci_gate.py
python3 -m unittest quality/tests/test_quality_gate.py -v
echo "Lab 14 pipeline completed successfully."
