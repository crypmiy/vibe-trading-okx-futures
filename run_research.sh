#!/usr/bin/env bash
# One research cycle: data → agent report → forecast log → gate → signals for Freqtrade.
# Usage: ./run_research.sh [instrument ...]   (default: research/instruments.txt)
# Env: VT_DATA=local|colab (default local), AGENT_CMD (default: gemini headless), AGENT_SKIP=1 to only score.
set -euo pipefail
cd "$(dirname "$0")"
set -a; [ -f .env ] && . ./.env; set +a
[ -d .venv ] || python3 -m venv .venv
. .venv/bin/activate
pip install -q -r requirements.txt
DATE=$(date -u +%F)
INSTRUMENTS=("$@"); [ ${#INSTRUMENTS[@]} -eq 0 ] && mapfile -t INSTRUMENTS < research/instruments.txt
AGENT_CMD="${AGENT_CMD:-scripts/agent.sh}"

for INST in "${INSTRUMENTS[@]}"; do
  echo "== $INST $DATE"
  if [ "${VT_DATA:-local}" = colab ]; then ./run_colab.sh "$INST" || { echo "[colab] failed, using local"; python scripts/pipeline.py "$INST" --out out; }; else python scripts/pipeline.py "$INST" --out out; fi
  if [ "${AGENT_SKIP:-0}" != 1 ]; then
    PROMPT=$(sed "s/{{DATE}}/$DATE/g; s/{{CONTRACT}}/$INST/g" prompt.md)
    $AGENT_CMD "Read AGENTS.md. The pipeline has already been run; its output is in ./out. Then do this: $PROMPT" \
      > "reports/${INST}_agent_${DATE}.log" 2>&1 || { echo "[agent] failed for $INST"; python scripts/notify.py "vibe: agent failed for $INST $DATE (see reports/${INST}_agent_${DATE}.log)"; }
    LATEST=$(ls -t reports/${INST}_OKX_Swap_Report_*.md 2>/dev/null | head -1 || true)
    [ -z "$LATEST" ] || python scripts/notify.py "$(python - "$LATEST" << 'PY'
import json,re,sys
t=open(sys.argv[1],errors="ignore").read(); m=re.search(r"```json\s*(\{.*?\})\s*```",t,re.S)
f=json.loads(m.group(1))["forecast"] if m else {}
s=re.search(r"#+\s*Executive summary\s*\n(.*?)(?:\n#+|\Z)",t,re.S|re.I)
print(f"{f.get('instrument')} {f.get('date')}: {f.get('bias')} ({f.get('confidence')}) zone {f.get('entry_low')}–{f.get('entry_high')} stop {f.get('stop')} tgt {f.get('target1')}\n"+(s.group(1).strip()[:900] if s else ""))
PY
)"
  fi
done
python scripts/forecast_log.py ingest reports
python scripts/forecast_log.py evaluate
python scripts/forecast_log.py export-signals signals/active.json
python scripts/forecast_log.py gate | tee research/gate_latest.txt
python scripts/notify.py "vibe cycle $DATE done: ${INSTRUMENTS[*]}
$(head -2 research/gate_latest.txt)"
