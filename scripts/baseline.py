"""Control group for the AI analyst (pre-registered, see research/GATES.md).

For every protocol-v2 directional AI forecast, two mechanical baselines trade the
same instrument over the same window with the same risk geometry:

  always_long   LONG  at the open of the first full 1h candle after the report
  always_short  SHORT at the same price

Stop and target distances are copied from the AI forecast (measured from the middle
of its entry zone), so only *direction and entry selection* differ. Scoring rules are
identical to the AI's: stop wins same-candle ties, horizon exit at the close of the
candle containing the horizon end, fees + slippage + realized funding deducted.

The gate compares the AI's mean R per directional forecast (not_entered = 0 R) with
the better of the two baselines — i.e. the AI must beat the hindsight-best constant
direction for the same period.
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS baselines (
  forecast_id TEXT, variant TEXT, status TEXT DEFAULT 'open',
  entry_at TEXT, entry_px REAL, exit_at TEXT, exit_px REAL, outcome TEXT,
  r_gross REAL, r_net REAL, evaluated_at TEXT,
  PRIMARY KEY (forecast_id, variant)
);
"""
VARIANTS = {"always_long": 1, "always_short": -1}
H1 = dt.timedelta(hours=1)


def evaluate_baselines(c) -> None:
    import forecast_log as fl
    import okx_futures as gf
    G = fl.GATES
    c.executescript(SCHEMA)
    now = dt.datetime.now(dt.timezone.utc)
    rows = c.execute("SELECT * FROM forecasts WHERE bias IN ('LONG','SHORT') AND made_at >= ?",
                     (G.get("count_from", "0000-00-00"),)).fetchall()
    candles, funding = {}, {}
    for r in rows:
        created = fl._created(r)
        start = (created + dt.timedelta(minutes=59)).replace(minute=0, second=0, microsecond=0)
        horizon_end = created + dt.timedelta(days=r["horizon_days"])
        if now < start or None in (r["entry_low"], r["entry_high"], r["stop"], r["target1"]):
            continue
        mid = (r["entry_low"] + r["entry_high"]) / 2
        d_stop, d_tgt = abs(mid - r["stop"]), abs(r["target1"] - mid)
        if d_stop <= 0 or d_tgt <= 0:
            continue
        for variant, side in VARIANTS.items():
            done = c.execute("SELECT status FROM baselines WHERE forecast_id=? AND variant=?",
                             (r["id"], variant)).fetchone()
            if done and done["status"] == "closed":
                continue
            inst = r["instrument"]
            if inst not in candles:
                days = max(2, (now - start).days + 2)
                candles[inst] = gf.candles(inst, "1h", days)
                funding[inst] = gf.funding_history(inst, 200)
            df = candles[inst]
            df = df[df.index >= start]
            if df.empty:
                continue
            entry = float(df.open.iloc[0])
            stop_px, tgt_px = entry - side * d_stop, entry + side * d_tgt
            outcome = exit_at = exit_px = None
            for t, k in df.iterrows():
                stop_hit = k.low <= stop_px if side == 1 else k.high >= stop_px
                tgt_hit = k.high >= tgt_px if side == 1 else k.low <= tgt_px
                if stop_hit:
                    outcome, exit_at, exit_px = "stop", t, stop_px; break
                if tgt_hit:
                    outcome, exit_at, exit_px = "target1", t, tgt_px; break
                if t + H1 >= horizon_end:
                    outcome, exit_at, exit_px = "horizon", t, float(k.close); break
            if outcome is None:
                if now < horizon_end:
                    continue
                outcome, exit_at, exit_px = "horizon", df.index[-1], float(df.close.iloc[-1])
            fh = funding[inst]
            f = fh[(fh.index > df.index[0]) & (fh.index <= exit_at)] if not fh.empty else fh
            funding_pct = float(f.funding_rate.sum()) if len(f) else 0.0
            cost_pct = 2 * (G["fee_taker_per_side"] + G["slippage_per_side"])
            r_gross = side * (exit_px - entry) / d_stop
            r_net = r_gross - (cost_pct + side * funding_pct) * entry / d_stop
            c.execute("""INSERT OR REPLACE INTO baselines(forecast_id, variant, status, entry_at, entry_px,
                         exit_at, exit_px, outcome, r_gross, r_net, evaluated_at)
                         VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                      (r["id"], variant, "closed", df.index[0].isoformat(), entry, exit_at.isoformat(),
                       exit_px, outcome, r_gross, r_net, now.isoformat()))
    c.commit()


def compare(c, closed_ai_rows) -> dict:
    """AI mean R per directional forecast (not_entered = 0) vs baselines on the same forecasts."""
    c.executescript(SCHEMA)
    ids = [r["id"] for r in closed_ai_rows]
    out = {"n_ai": len(ids)}
    if not ids:
        return out
    out["ai"] = sum((r["r_net"] or 0.0) if r["outcome"] != "not_entered" else 0.0
                    for r in closed_ai_rows) / len(ids)
    q = ",".join("?" * len(ids))
    for v in VARIANTS:
        rs = [x["r_net"] for x in c.execute(
            f"SELECT r_net FROM baselines WHERE variant=? AND status='closed' AND forecast_id IN ({q})", (v, *ids))]
        out[f"n_{v}"] = len(rs)
        out[v] = sum(rs) / len(rs) if rs else None
    return out
