#!/usr/bin/env -S colab run --keep -s vibe --timeout 600
"""One-shot data + analysis pipeline for an OKX USDT-margined perpetual (SWAP).

Runs identically on:
  * a Colab VM:   colab run --keep -s vibe --timeout 600 scripts/pipeline.py BTC-USDT-SWAP
  * the Jetson:   python scripts/pipeline.py BTC-USDT-SWAP

Writes to --out (default /content/vt_out on Colab, ./out locally):
  summary.json              everything the agent needs, in one file
  <contract>_<tf>.csv       OHLCV per timeframe
  funding.csv, contract_stats.csv
  chart_<tf>.png, chart_derivatives.png
  vt_out.tar.gz             bundle for `colab download`
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
import sys
import tarfile
from pathlib import Path

# make sibling modules importable both as a file and when pasted into a kernel
HERE = Path(__file__).resolve().parent if "__file__" in globals() else Path.cwd()
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "scripts"))


def ensure_deps() -> None:
    try:
        import pandas, requests, matplotlib  # noqa: F401
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pandas", "numpy", "requests", "matplotlib"], check=True)


def fetch_sources_if_missing() -> None:
    """On Colab the kernel only receives pipeline.py; pull the two modules from GitHub."""
    import urllib.request
    repo_raw = os.environ.get("VT_RAW", "https://raw.githubusercontent.com/crypmiy/vibe-trading-okx-futures/main/scripts")
    for name in ("okx_futures.py", "analyze.py"):
        if not (HERE / name).exists() and not (HERE / "scripts" / name).exists():
            urllib.request.urlretrieve(f"{repo_raw}/{name}", HERE / name)


BARS_PER_DAY = {"1h": 24, "4h": 6, "1d": 1}


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("contract", nargs="?", default="BTC-USDT-SWAP", help="OKX USDT swap, e.g. BTC-USDT-SWAP (BTC or BTC_USDT also accepted)")
    p.add_argument("--intervals", default="1h,4h,1d")
    p.add_argument("--days", type=int, default=365, help="history for the 1d/4h series")
    p.add_argument("--out", default="/content/vt_out" if Path("/content").exists() else "out")
    a = p.parse_args(argv)

    ensure_deps()
    fetch_sources_if_missing()
    import pandas as pd
    import okx_futures as gf
    import analyze as an

    out = Path(a.out); out.mkdir(parents=True, exist_ok=True)
    contract = gf.normalize_inst(a.contract)
    print(f"[vt] {contract} → {out}", flush=True)

    info = gf.contract_info(contract)
    tk = gf.ticker(contract)
    funding_h = gf.funding_interval_hours(tk)
    print(f"[vt] instrument ok, funding every {funding_h:g}h, last={tk.get('last')}", flush=True)

    frames: dict[str, pd.DataFrame] = {}
    tf_summaries = {}
    for tf in a.intervals.split(","):
        days = a.days if tf in ("1d", "4h") else min(a.days, 60)
        df = gf.candles(contract, tf, days)
        if df.empty:
            print(f"[vt] no candles for {tf}", flush=True); continue
        frames[tf] = df
        df.to_csv(out / f"{contract}_{tf}.csv")
        tf_summaries[tf] = an.timeframe_summary(df, tf, BARS_PER_DAY.get(tf, 24))
        an.chart_price(df, tf, contract, out / f"chart_{tf}.png")
        print(f"[vt] {tf}: {len(df)} bars", flush=True)

    fund = gf.funding_history(contract)
    cs = gf.contract_stats(contract, "1h", 100)
    liq = gf._safe(gf.liquidations, contract)
    if not liq.empty:
        cs = pd.concat([cs, liq.reindex(cs.index).fillna(0)], axis=1) if not cs.empty else liq
    fund.to_csv(out / "funding.csv"); cs.to_csv(out / "contract_stats.csv")
    hourly = frames.get("1h", next(iter(frames.values()))).close
    spot = gf.spot_close(contract, "1h", 60)
    an.chart_derivatives(fund, cs, hourly, contract, out / "chart_derivatives.png")

    summary = {
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "exchange": "okx", "market": "USDT-margined perpetual swap", "contract": contract,
        "contract_specs": {k: info.get(k) for k in (
            "instId", "uly", "ctVal", "ctValCcy", "ctMult", "ctType", "lever", "tickSz", "lotSz",
            "minSz", "maxLmtSz", "maxMktSz", "settleCcy", "state", "listTime", "expTime")},
        "funding_interval_hours": funding_h,
        "ticker": tk,
        "timeframes": tf_summaries,
        "funding": an.funding_summary(fund, funding_h),
        "positioning": an.positioning_summary(cs, hourly),
        "basis": an.basis_summary(tk, hourly, spot),
        "files": sorted(f.name for f in out.iterdir()),
        "caveats": [
            "contract_stats (OI, long/short account ratio, taker ratio) comes from OKX Rubik trading-data endpoints and is aggregated per currency across OKX contracts, not per instrument",
            "liquidation sizes cover only the most recent ~100 forced orders returned by the public endpoint",
            "volume_contracts is in contracts; multiply by ctVal for base units",
            "basis uses the OKX index (spot basket) as the spot reference",
            "all timestamps UTC; last candle may be incomplete",
        ],
    }
    an.write_json(summary, out / "summary.json")

    with tarfile.open(out / "vt_out.tar.gz", "w:gz") as t:
        for f in out.iterdir():
            if f.name != "vt_out.tar.gz":
                t.add(f, arcname=f.name)
    print(f"[vt] done — {len(summary['files'])} files, bundle {out / 'vt_out.tar.gz'}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
