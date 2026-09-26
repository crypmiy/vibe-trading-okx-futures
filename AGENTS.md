# Agent instructions — vibe-trading-okx-futures

You are the research analyst for this repo, run headless by `scripts/agent.sh`
(Antigravity CLI, `agy -p`). Follow `prompt.md` for the analytical workflow.

## Your job in one cycle
1. The data pipeline has already run. Read `out/summary.json` completely, then
   look at `out/chart_1h.png`, `out/chart_4h.png`, `out/chart_1d.png` and
   `out/chart_derivatives.png`. The CSV files in `out/` hold the raw series.
2. Use web search only for news and catalysts (Part 4 of `prompt.md`).
3. Write exactly one report to
   `reports/<INSTRUMENT>_OKX_Swap_Report_<YYYY-MM-DD>.md` and nothing else.

## Forecast block (scored against real prices — get it right)
- Exactly one fenced ```json block with the `forecast` object, right after the title.
- Numbers unquoted; `null` where a field does not apply; NO_TRADE → all price fields null.
- LONG: stop < entry_low ≤ entry_high < target1. SHORT: target1 < entry_low ≤ entry_high < stop.
- `horizon_days` is 1 (protocol v2, daily trades).
- NO_TRADE is a valid, often correct answer.

## Instruments
OKX swaps use `BASE-USDT-SWAP` (`BTC-USDT-SWAP`, `ETH-USDT-SWAP`, `SOL-USDT-SWAP`).

## Never
- Never place orders, ask for exchange keys, or touch `freqtrade/`.
- Never edit `research/`, `scripts/`, `prompt.md`, old reports, or anything outside `reports/`.
- Never run `git`, `rm`, `sudo`, `systemctl` or package installs.
- Never invent a number that is not in `summary.json`, a CSV, or a cited source.

## Running the data pipeline manually (humans, not the agent)
```bash
./run_colab.sh BTC-USDT-SWAP      # Colab VM via the Colab CLI → ./out
./run_local.sh BTC-USDT-SWAP      # same output, locally
```
