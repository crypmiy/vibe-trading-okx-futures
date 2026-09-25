# Pre-registered research plan — vibe-trading-okx-futures

Written **before** any forecast is scored. Do not edit thresholds after data
exists; if a threshold must change, add a dated note and restart the count.

## Hypothesis
H1: LLM-written derivatives theses (prompt.md, OKX data pipeline) have positive
net expectancy when executed mechanically (entry zone → stop / target1 / horizon).

## Phase 1 — forecast log (paper, $0)
Cadence: every Monday and Thursday for the instruments in `research/instruments.txt`.
Each report carries a machine-readable forecast block (see prompt.md).
Scoring (`scripts/forecast_log.py evaluate`), all pessimistic:
- Entered only if 1h close range touches the entry zone within 48 h of the report.
- After entry, first touch of stop vs target1 decides; same candle touching both = stop.
- Untouched by horizon → closed at horizon close (mark-to-market).
- R = (exit − entry)/(entry − stop) signed by side, minus fees 0.05 %/side,
  slippage 0.05 %/side and realized funding over the hold.
Gate (research/gates.json): ≥30 directional forecasts, ≥50 % entered,
hit rate to target1 ≥50 %, expectancy ≥ +0.10 R net, AND both temporal halves
(first 15 vs next 15) positive. NO TRADE calls are logged but do not count.
Failing the gate = confirmed negative result; the project stops there.

## Phase 2 — Freqtrade dry-run (paper, $0)
Only if Phase 1 passes. `freqtrade/` runs OKX futures dry-run (wallet 1000 USDT,
1× leverage) driven by `signals/active.json` exported from the forecast log.
Gate: ≥20 closed dry-run trades, dry-run expectancy ≥ +0.10 R net, and the gap
between dry-run R and forecast-log R ≤ 0.25 R per trade (execution realism).

## Phase 3 — live (only after Phase 2)
Risk 0.5–1 % of equity per trade at the stop. Not part of this repo's automation.

## Notes log
- 2026-09-25: plan registered.
