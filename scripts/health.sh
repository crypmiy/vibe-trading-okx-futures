#!/usr/bin/env bash
# Health check for vibe-trading-okx-futures. Usage: ./scripts/health.sh
cd "$(dirname "$0")/.." || exit 1
TODAY=$(date -u +%F)
ok=0; bad=0
pass() { echo "  ✓ $1"; ok=$((ok+1)); }
fail() { echo "  ✗ $1"; bad=$((bad+1)); }
chk()  { if eval "$2" >/dev/null 2>&1; then pass "$1"; else fail "$1"; fi; }

echo "[1/5] services"
chk "Telegram bot (vibe-tgbot) running"      "systemctl is-active --quiet vibe-tgbot"
chk "Freqtrade dry-run (vibe-freqtrade) running" "systemctl is-active --quiet vibe-freqtrade"
chk "research timer enabled"                 "systemctl is-active --quiet vibe-research.timer"
chk "scoring timer enabled"                  "systemctl is-active --quiet vibe-score.timer"

echo "[2/5] today's research cycle ($TODAY UTC)"
n=$(ls reports/*_OKX_Swap_Report_"$TODAY"*.md 2>/dev/null | wc -l)
want=$(grep -c . research/instruments.txt)
[ "$n" -ge "$want" ] && pass "reports today: $n/$want" || fail "reports today: $n/$want"
last=$(systemctl show vibe-research -p ExecMainStatus --value)
[ "$last" = 0 ] && pass "last research run exited OK" || fail "last research run exit status: $last"
errs=$(grep -liE "error|quota|unauth|login" reports/*_agent_"$TODAY"*.log 2>/dev/null | wc -l)
[ "$errs" = 0 ] && pass "agent logs today clean" || fail "agent logs with errors today: $errs"

echo "[3/5] forecast log"
. .venv/bin/activate
python - << 'PY'
import sqlite3, datetime as dt
c = sqlite3.connect("research/forecasts.sqlite")
last = c.execute("SELECT max(made_at) FROM forecasts").fetchone()[0]
today = dt.datetime.now(dt.timezone.utc).date().isoformat()
print(("  ✓" if (last or "").startswith(today) else "  ✗") + f" latest forecast date: {last}")
op = c.execute("SELECT count(*) FROM forecasts WHERE status IN ('open','entered') AND bias IN ('LONG','SHORT')").fetchone()[0]
print(f"  · open/entered forecasts: {op}")
PY
head -2 research/gate_latest.txt 2>/dev/null | sed 's/^/  · /'

echo "[4/5] freqtrade"
FT=$(python -c "import json;c=json.load(open('freqtrade/config.dryrun.json'))['api_server'];print(c['username']+':'+c['password'],c['listen_port'])" 2>/dev/null)
AUTH=${FT% *}; PORT=${FT#* }
if curl -s -m 5 "http://127.0.0.1:$PORT/api/v1/ping" | grep -q pong; then
  pass "API responding on :$PORT"
  st=$(curl -s -m 5 -u "$AUTH" "http://127.0.0.1:$PORT/api/v1/show_config" | python -c "import sys,json;print(json.load(sys.stdin).get('state','?'))" 2>/dev/null)
  [ "$st" = running ] && pass "bot state: running" || fail "bot state: ${st:-unknown (auth?)}"
  curl -s -m 5 -u "$AUTH" "http://127.0.0.1:$PORT/api/v1/count" | python -c "import sys,json;d=json.load(sys.stdin);print(f'  · open trades: {d[\"current\"]}/{d[\"max\"]}')" 2>/dev/null
else
  fail "API not responding on :$PORT"
fi
since=$(journalctl -u vibe-freqtrade --since "-2h" --no-pager -q 2>/dev/null | grep -c "heartbeat")
[ "$since" -gt 0 ] && pass "heartbeat in last 2h" || fail "no heartbeat in last 2h"

echo "[5/5] GitHub"
git fetch -q origin 2>/dev/null
lc=$(git log -1 --format=%cs origin/main 2>/dev/null)
[ "$lc" = "$TODAY" ] && pass "auto-push today ($lc)" || fail "last push: ${lc:-unknown}"

echo
if [ "$bad" = 0 ]; then echo "SEMUA SEHAT ($ok cek lolos)"; else echo "ADA MASALAH: $bad gagal, $ok lolos — lihat tanda ✗"; fi
