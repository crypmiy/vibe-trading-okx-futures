#!/usr/bin/env python3
"""Research Telegram bot (long polling, single chat). Commands:

/gate            pre-registered gate status (one-line verdict first)
/open            open / entered forecasts
/last [INST]     executive summary of the latest report (default: all instruments)
/signals         what the Freqtrade strategy currently sees
/run [INST...]   start a research cycle in the background (data → agent → score)
/score           re-score open forecasts now
/help
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import time
from contextlib import redirect_stdout
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import notify  # noqa: E402

notify.load_env()
TOKEN, CHAT = os.environ["TG_TOKEN"], str(os.environ["TG_CHAT_ID"])
API = f"https://api.telegram.org/bot{TOKEN}"
JOBS: dict[str, subprocess.Popen] = {}


def capture(fn, *a) -> str:
    buf = io.StringIO()
    with redirect_stdout(buf):
        fn(*a)
    return buf.getvalue().strip() or "(no output)"


def cmd_gate(_: list[str]) -> str:
    import forecast_log as fl
    return capture(fl.gate)


def cmd_score(_: list[str]) -> str:
    import forecast_log as fl
    out = capture(fl.evaluate)
    fl.export_signals(ROOT / "signals" / "active.json")
    return (out + "\n\n" + capture(fl.gate))[:4000]


def cmd_open(_: list[str]) -> str:
    import forecast_log as fl
    rows = fl.db().execute("SELECT instrument,made_at,bias,confidence,entry_low,entry_high,stop,target1,status,entry_px "
                           "FROM forecasts WHERE bias IN ('LONG','SHORT') AND status IN ('open','entered') ORDER BY made_at").fetchall()
    if not rows:
        return "no open forecasts"
    return "\n".join(f"{r['instrument']} {r['made_at']} {r['bias']} ({r['confidence']}) "
                     f"zone {r['entry_low']}–{r['entry_high']} stop {r['stop']} tgt {r['target1']} · {r['status']}"
                     + (f" @ {r['entry_px']}" if r['entry_px'] else "") for r in rows)


def cmd_last(args: list[str]) -> str:
    reports = sorted((ROOT / "reports").glob("*_OKX_Swap_Report_*.md"))
    if args:
        reports = [p for p in reports if p.name.upper().startswith(args[0].upper())]
    latest: dict[str, Path] = {}
    for p in reports:
        latest[p.name.split("_OKX")[0]] = p
    if not latest:
        return "no reports yet"
    out = []
    for inst, p in latest.items():
        txt = p.read_text(errors="ignore")
        m = re.search(r"```json\s*(\{.*?\})\s*```", txt, re.S)
        f = json.loads(m.group(1))["forecast"] if m else {}
        summ = re.search(r"#+\s*Executive summary\s*\n(.*?)(?:\n#+|\Z)", txt, re.S | re.I)
        body = summ.group(1).strip() if summ else "(no executive summary found)"
        out.append(f"— {inst} ({f.get('date','?')}): {f.get('bias','?')} {f.get('confidence','')}\n{body[:900]}")
    return "\n\n".join(out)[:4000]


def cmd_signals(_: list[str]) -> str:
    p = ROOT / "signals" / "active.json"
    if not p.exists():
        return "signals/active.json not generated yet"
    s = json.loads(p.read_text())["signals"]
    return "no active signals" if not s else "\n".join(
        f"{x['pair']} {x['side']} zone {x['entry_low']}–{x['entry_high']} stop {x['stop']} tgt {x['target1']} until {x['expires_at'][:10]}" for x in s)


def cmd_run(args: list[str]) -> str:
    if "research" in JOBS and JOBS["research"].poll() is None:
        return "a research cycle is already running"
    log = open(ROOT / "research" / "run_latest.log", "w")
    JOBS["research"] = subprocess.Popen([str(ROOT / "run_research.sh"), *args], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
    return f"started research cycle for {' '.join(args) or 'research/instruments.txt'} — results will be posted here"


COMMANDS = {"/gate": cmd_gate, "/open": cmd_open, "/last": cmd_last, "/signals": cmd_signals,
            "/run": cmd_run, "/score": cmd_score, "/help": lambda _: __doc__.strip()}


def handle(text: str) -> str:
    parts = text.split()
    cmd = parts[0].split("@")[0].lower()
    fn = COMMANDS.get(cmd)
    if not fn:
        return "unknown command — /help"
    try:
        return fn(parts[1:])
    except Exception as e:  # noqa: BLE001
        return f"error: {e}"


def main() -> None:
    offset = None
    notify.send("vibe research bot online — /help", silent=True)
    while True:
        try:
            r = requests.get(f"{API}/getUpdates", params={"timeout": 50, "offset": offset}, timeout=60).json()
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                m = u.get("message") or {}
                if str(m.get("chat", {}).get("id")) != CHAT or not m.get("text", "").startswith("/"):
                    continue
                notify.send(handle(m["text"]))
        except Exception as e:  # noqa: BLE001
            print(f"[tg_bot] {e}", flush=True); time.sleep(5)


if __name__ == "__main__":
    main()
