#!/usr/bin/env bash
# Run the OKX swap pipeline on a Google Colab VM via the Colab CLI, then fetch results.
# Usage: ./run_colab.sh BTC-USDT-SWAP [extra pipeline args]
set -euo pipefail
CONTRACT="${1:-BTC-USDT-SWAP}"; shift || true
SESSION="${VT_SESSION:-vibe}"

command -v colab >/dev/null || { echo "colab CLI missing: pip install google-colab-cli (or uv tool install google-colab-cli)"; exit 1; }
# One-time auth (interactive, human required):
#   gcloud auth application-default login \
#     --scopes=openid,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/colaboratory

mkdir -p out
trap 'colab stop -s "$SESSION" >/dev/null 2>&1 || true' EXIT
colab run --keep -s "$SESSION" --timeout 600 scripts/pipeline.py "$CONTRACT" --out /content/vt_out "$@"
colab download -s "$SESSION" /content/vt_out/vt_out.tar.gz out/vt_out.tar.gz
tar -xzf out/vt_out.tar.gz -C out
echo "[run_colab] results in ./out — summary: out/summary.json"
