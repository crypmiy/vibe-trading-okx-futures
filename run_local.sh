#!/usr/bin/env bash
# Same pipeline, run locally in a venv (Jetson / laptop). Usage: ./run_local.sh BTC-USDT-SWAP [extra args]
set -euo pipefail
cd "$(dirname "$0")"
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
python scripts/pipeline.py "${1:-BTC-USDT-SWAP}" --out out "${@:2}"
