#!/usr/bin/env bash
# Research agent via Antigravity CLI (agy).
# AGY_MODEL: model slug (see: agy models).
# AGY_TTY=1: run under a pseudo-TTY if -p hangs.
P=$(mktemp)
printf '%s' "$1" > "$P"
ARGS="--dangerously-skip-permissions --print-timeout 20m"
[ -n "$AGY_MODEL" ] && ARGS="$ARGS --model $AGY_MODEL"
CMD="agy $ARGS -p \"\$(cat $P)\""
for round in 1 2; do
  echo "[agent.sh] round $round model ${AGY_MODEL:-default}" >&2
  if [ "${AGY_TTY:-0}" = 1 ]; then
    timeout 25m script -qec "$CMD" /dev/null && { rm -f "$P"; exit 0; }
  else
    timeout 25m bash -c "$CMD" && { rm -f "$P"; exit 0; }
  fi
  if [ "$round" = 1 ]; then
    echo "[agent.sh] failed, wait 5 min" >&2
    sleep 300
  fi
done
rm -f "$P"
exit 1
