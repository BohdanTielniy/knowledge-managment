#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=.
python3 agent/graph_agent.py
python3 mcp_server/server.py
python3 agent/eval_scenarios.py
python3 agent/red_team.py
python3 agent/propose_fact.py
echo "Lab 15 pipeline completed successfully."
