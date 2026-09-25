#!/usr/bin/env python3
"""Forecast log: ingest report forecast blocks → SQLite, score them against OKX
prices pessimistically, print the pre-registered gate, export active signals
for the Freqtrade dry-run strategy.

  python scripts/forecast_log.py ingest [reports/]
  python scripts/forecast_log.py evaluate
  python scripts/forecast_log.py gate
  python scripts/forecast_log.py export-signals [signals/active.json]
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import math
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
DB = ROOT / "research" / "forecasts.sqlite"
def _notify(text: str) -> None:
    try:
        import notify
        notify.send(text, silent=True)
    except Exception:  # noqa: BLE001
        pass

GATES = json.loads((ROOT / "research" / "gates.json").read_text())["phase1_forecast_gate"]

SCHEMA = """
CREATE TABLE IF NOT EXISTS forecasts (
  id TEXT PRIMARY KEY, report TEXT, instrument TEXT, made_at TEXT, bias TEXT, confidence TEXT,
  entry_low REAL, entry_high REAL, stop REAL, target1 REAL, target2 REAL, horizon_days INTEGER,
  status TEXT DEFAULT 'open', entered_at TEXT, entry_px REAL, exit_at TEXT, exit_px REAL,
  outcome TEXT, r_gross REAL, r_net REAL, funding_pct REAL, evaluated_at TEXT
);
"""

def db() -> sqlite3.Connection:
    DB.parent.mkdir(exist_ok=True)
    c = sqlite3.connect(DB); c.executescript(SCHEMA); c.row_factory = sqlite3.Row
    return c


# ---------- ingest ----------
BLOCK = re.compile(r"```json\s*(\{.*?\"forecast\".*?\})\s*```", re.S)

def parse_report(path: Path) -> dict | None:
    m = BLOCK.search(path.read_text(errors="ignore"))
    if not m:
        return None
    f = json.loads(m.group(1))["forecast"]
    f["bias"] = f.get("bias", "NO_TRADE").upper().replace(" ", "_")
    return f

def ingest(folder: Path) -> None:
    c = db(); n = 0
    for p in sorted(folder.glob("*.md")):
        f = parse_report(p)
        if not f:
            print(f"[skip] no forecast block: {p.name}"); continue
        fid = hashlib.sha1(f"{f['instrument']}|{f['date']}|{p.name}".encode()).hexdigest()[:12]
        if c.execute("SELECT 1 FROM forecasts WHERE id=?", (fid,)).fetchone():
            continue
        c.execute("""INSERT INTO forecasts(id,report,instrument,made_at,bias,confidence,entry_low,entry_high,
                     stop,target1,target2,horizon_days) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
                  (fid, p.name, f["instrument"], f["date"], f["bias"], f.get("confidence"),
                   f.get("entry_low"), f.get("entry_high"), f.get("stop"), f.get("target1"),
                   f.get("target2"), int(f.get("horizon_days", 7))))
        n += 1
    c.commit(); print(f"[ingest] {n} new forecast(s), db={DB}")


# ---------- evaluate ----------
def evaluate() -> None:
    import okx_futures as gf
    c = db()
    rows = c.execute("SELECT * FROM forecasts WHERE status='open' AND bias IN ('LONG','SHORT')").fetchall()
    now = dt.datetime.now(dt.timezone.utc)
    for r in rows:
        made = dt.datetime.fromisoformat(r["made_at"]).replace(tzinfo=dt.timezone.utc)
        horizon_end = made + dt.timedelta(days=r["horizon_days"])
        days = max(1, math.ceil((now - made).total_seconds() / 86400) + 1)
        df = gf.candles(r["instrument"], "1h", days)
        df = df[df.index >= made]
        if df.empty:
            continue
        side = 1 if r["bias"] == "LONG" else -1
        lo, hi = sorted([r["entry_low"], r["entry_high"]])
        win = df[df.index <= made + dt.timedelta(hours=GATES["entry_window_hours"])]
        hit = win[(win.low <= hi) & (win.high >= lo)]
        if hit.empty:
            if now > made + dt.timedelta(hours=GATES["entry_window_hours"]):
                c.execute("UPDATE forecasts SET status='closed', outcome='not_entered', evaluated_at=? WHERE id=?",
                          (now.isoformat(), r["id"]))
            continue
        entered_at = hit.index[0]
        entry_px = min(max(float(hit.close.iloc[0]), lo), hi)  # pessimistic: fill inside the zone at the close
        after = df[df.index > entered_at]
        outcome, exit_at, exit_px = None, None, None
        for t, k in after.iterrows():
            stop_hit = k.low <= r["stop"] if side == 1 else k.high >= r["stop"]
            tgt_hit = k.high >= r["target1"] if side == 1 else k.low <= r["target1"]
            if stop_hit:                       # stop wins ties (pre-registered)
                outcome, exit_at, exit_px = "stop", t, r["stop"]; break
            if tgt_hit:
                outcome, exit_at, exit_px = "target1", t, r["target1"]; break
            if t >= horizon_end:
                outcome, exit_at, exit_px = "horizon", t, float(k.close); break
        if outcome is None:
            if now < horizon_end:
                c.execute("UPDATE forecasts SET status='entered', entered_at=?, entry_px=? WHERE id=?",
                          (entered_at.isoformat(), entry_px, r["id"]))
                continue
            outcome, exit_at, exit_px = "horizon", after.index[-1], float(after.close.iloc[-1])
        risk = abs(entry_px - r["stop"])
        r_gross = side * (exit_px - entry_px) / risk if risk else 0.0
        cost_pct = 2 * (GATES["fee_taker_per_side"] + GATES["slippage_per_side"])
        fund = gf.funding_history(r["instrument"], 200)
        fund = fund[(fund.index > entered_at) & (fund.index <= exit_at)] if not fund.empty else fund
        funding_pct = float(fund.funding_rate.sum()) if len(fund) else 0.0   # longs pay positive funding
        cost_r = (cost_pct + side * funding_pct) * entry_px / risk
        r_net = r_gross - cost_r
        c.execute("""UPDATE forecasts SET status='closed', entered_at=?, entry_px=?, exit_at=?, exit_px=?, outcome=?,
                     r_gross=?, r_net=?, funding_pct=?, evaluated_at=? WHERE id=?""",
                  (entered_at.isoformat(), entry_px, exit_at.isoformat(), exit_px, outcome, r_gross, r_net,
                   funding_pct * 100, now.isoformat(), r["id"]))
        line = f"[eval] {r['instrument']} {r['made_at']} {r['bias']:5} → {outcome:11} R_net={r_net:+.2f}"
        print(line); _notify(line)
    c.commit()


# ---------- gate ----------
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (0.0, 0.0)
    p = k / n; d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (centre - half, centre + half)

def gate() -> None:
    c = db()
    directional = c.execute("SELECT * FROM forecasts WHERE bias IN ('LONG','SHORT') ORDER BY made_at").fetchall()
    closed = [r for r in directional if r["status"] == "closed"]
    entered = [r for r in closed if r["outcome"] != "not_entered"]
    n_dir, n_ent = len(closed), len(entered)
    hits = sum(r["outcome"] == "target1" for r in entered)
    rs = [r["r_net"] for r in entered]
    exp = sum(rs) / len(rs) if rs else 0.0
    half = len(entered) // 2
    exp1 = sum(r["r_net"] for r in entered[:half]) / half if half else 0.0
    exp2 = sum(r["r_net"] for r in entered[half:]) / (len(entered) - half) if len(entered) - half else 0.0
    lo, hi = wilson(hits, n_ent)
    checks = {
        f"≥{GATES['min_directional_forecasts']} directional forecasts scored": n_dir >= GATES["min_directional_forecasts"],
        f"≥{GATES['min_entered_share']:.0%} entered": n_dir > 0 and n_ent / n_dir >= GATES["min_entered_share"],
        f"hit rate ≥{GATES['min_hit_rate_target1']:.0%}": n_ent > 0 and hits / n_ent >= GATES["min_hit_rate_target1"],
        f"expectancy ≥ +{GATES['min_expectancy_r_net']:.2f} R net": exp >= GATES["min_expectancy_r_net"],
        "both temporal halves positive": half > 0 and exp1 > 0 and exp2 > 0,
    }
    passed = all(checks.values())
    sample_ok = n_dir >= GATES["min_directional_forecasts"]
    verdict = ("GATE PASSED — proceed to Phase 2 (Freqtrade dry-run)" if passed else
               "GATE FAILED — confirmed negative result" if sample_ok else
               f"NOT YET DECIDABLE — {n_dir}/{GATES['min_directional_forecasts']} directional forecasts scored")
    print(verdict)
    print(f"  entered {n_ent}/{n_dir} · hit rate {hits}/{n_ent} (95% CI {lo:.0%}–{hi:.0%}) · "
          f"expectancy {exp:+.2f} R net · halves {exp1:+.2f} / {exp2:+.2f}")
    for k, v in checks.items():
        print(f"  [{'x' if v else ' '}] {k}")
    open_n = c.execute("SELECT COUNT(*) FROM forecasts WHERE status IN ('open','entered') AND bias IN ('LONG','SHORT')").fetchone()[0]
    nt = c.execute("SELECT COUNT(*) FROM forecasts WHERE bias='NO_TRADE'").fetchone()[0]
    print(f"  open/entered: {open_n} · NO_TRADE calls: {nt}")


# ---------- export for freqtrade ----------
def export_signals(path: Path) -> None:
    c = db()
    now = dt.datetime.now(dt.timezone.utc)
    out = []
    for r in c.execute("SELECT * FROM forecasts WHERE bias IN ('LONG','SHORT') AND status IN ('open','entered')"):
        made = dt.datetime.fromisoformat(r["made_at"]).replace(tzinfo=dt.timezone.utc)
        out.append({"instrument": r["instrument"], "pair": r["instrument"].replace("-USDT-SWAP", "/USDT:USDT"),
                    "side": r["bias"].lower(), "entry_low": r["entry_low"], "entry_high": r["entry_high"],
                    "stop": r["stop"], "target1": r["target1"], "made_at": r["made_at"],
                    "entry_deadline": (made + dt.timedelta(hours=GATES["entry_window_hours"])).isoformat(),
                    "expires_at": (made + dt.timedelta(days=r["horizon_days"])).isoformat(), "forecast_id": r["id"]})
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps({"generated_utc": now.isoformat(), "signals": out}, indent=2))
    print(f"[export] {len(out)} active signal(s) → {path}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "gate"
    if cmd == "ingest":
        ingest(Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "reports")
    elif cmd == "evaluate":
        evaluate()
    elif cmd == "gate":
        gate()
    elif cmd == "export-signals":
        export_signals(Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / "signals" / "active.json")
    else:
        print(__doc__); sys.exit(2)
