#!/usr/bin/env bash
# Runs the research agent with model fallback. Usage: scripts/agent.sh "<prompt>"
# GEMINI_MODELS: space-separated, tried in order; "default" = the CLI's own default model.
MODELS="${GEMINI_MODELS:-default gemini-2.5-flash}"
for round in 1 2; do
  for m in $MODELS; do
    echo "[agent.sh] round $round, model $m" >&2
    if [ "$m" = default ]; then timeout 20m gemini --yolo -p "$1" && exit 0
    else timeout 20m gemini -m "$m" --yolo -p "$1" && exit 0; fi
  done
  [ "$round" = 1 ] && { echo "[agent.sh] all models failed, waiting 5 min" >&2; sleep 300; }
done
exit 1
