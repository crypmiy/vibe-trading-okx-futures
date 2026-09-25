#!/usr/bin/env bash
# Agent with model fallback.
# GEMINI_MODELS in .env, tried in order.
# "default" = CLI default model.
MODELS="${GEMINI_MODELS:-default}"
for round in 1 2; do
  for m in $MODELS; do
    echo "[agent.sh] round $round model $m" >&2
    if [ "$m" = default ]; then
      timeout 20m gemini --yolo -p "$1" && exit 0
    else
      timeout 20m gemini -m "$m" --yolo -p "$1" && exit 0
    fi
  done
  if [ "$round" = 1 ]; then
    echo "[agent.sh] all failed, wait 5 min" >&2
    sleep 300
  fi
done
exit 1
