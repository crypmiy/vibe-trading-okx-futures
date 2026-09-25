# Agent instructions — vibe-trading-okx-futures

You are the research agent for this repo. Read `prompt.md` for the analytical
workflow; this file tells you how to get the data.

## What this repo is
A port of [wanghsinche/vibe-trading](https://github.com/wanghsinche/vibe-trading)
from US equities to **OKX USDT-margined perpetual swaps**. The
equity MCP data server is replaced by a public-API Python pipeline that you run on
a **Google Colab VM through the `colab` CLI** (or locally). Charts are generated
by the pipeline (matplotlib); the AntV chart MCP is optional extra.

## Data pipeline
```
scripts/pipeline.py <INSTRUMENT> [--intervals 1h,4h,1d] [--days 365] [--out DIR]
```
Output (`summary.json`, CSVs, PNG charts, `vt_out.tar.gz`). OI / long-short / taker
stats come from OKX trading-data endpoints and are per **currency**, not per instrument.. The pipeline only
needs `pandas numpy requests matplotlib` — all preinstalled on Colab.

### Preferred: run on Colab via the CLI
```bash
colab run --keep -s vibe --timeout 600 scripts/pipeline.py BTC-USDT-SWAP
colab download -s vibe /content/vt_out/vt_out.tar.gz out/vt_out.tar.gz
colab stop -s vibe
tar -xzf out/vt_out.tar.gz -C out
```
Notes for the agent:
- `colab run` forwards `sys.argv`, so pass the contract as a positional arg.
- `--keep` keeps the session alive so `colab download` can fetch the bundle;
  **always** `colab stop -s vibe` afterwards — an unstopped VM burns compute units.
- `colab run` only ships `pipeline.py` to the kernel; the pipeline downloads
  `okx_futures.py` and `analyze.py` from this repo's `main` branch on GitHub
  (override with `VT_RAW=<raw-url-to-scripts-dir>` if you are on a fork/branch).
- Never call `colab repl`, `colab console`, `colab auth` or `colab drivemount`
  interactively — they need a TTY. Auth for the CLI itself is `gcloud auth
  application-default login` with the Colab scopes (see `run_colab.sh`).
- If Colab is unavailable, fall back to the local run below; the output is identical.

### Fallback: run locally (Jetson / laptop)
```bash
./run_local.sh BTC-USDT-SWAP
```

## Instrument names
OKX swaps use `BASE-USDT-SWAP`: `BTC-USDT-SWAP`, `ETH-USDT-SWAP`, `SOL-USDT-SWAP`.
The pipeline also accepts `BTC` or `BTC_USDT` and normalizes them. If `contract_info`
reports the instrument is not found, tell the user rather than guessing.

## Writing the report
1. Fill `prompt.md` placeholders `{{DATE}}` and `{{CONTRACT}}`.
2. Read `out/summary.json` fully before writing anything.
3. Follow Part 0 → Part 5 in order. Facts before interpretation.
4. Save to `reports/<INSTRUMENT>_OKX_Swap_Report_<YYYY-MM-DD>.md` and copy the
   referenced PNGs into `reports/img/`.
5. "NO TRADE" is an acceptable and often correct conclusion.
6. The forecast block at the top of the report is parsed by `scripts/forecast_log.py`
   and scored later against real prices — a sloppy or inconsistent block wastes a
   sample. Check: stop and target1 on the correct sides of the entry zone, numbers
   unquoted, exactly one block per report. Do not edit or re-run old reports.

## Never
- Never place orders or request OKX API keys — this is research only.
- Never fabricate a number that is not in `summary.json`, a CSV, or a cited source.
