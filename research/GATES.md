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
- 2026-09-25: analyst = Antigravity CLI (agy), model gemini-3.8-flash-high, fixed for all Phase 1 samples.
- 2026-09-25: universe widened to 8 swaps (research/instruments.txt); added min 8 distinct cycle dates; temporal halves split by cycle date. Changed before the first forecast was scored.
- 2026-09-25: PROTOCOL v2 (daily). Hypothesis changed from multi-day swing to daily trades: BTC/ETH/SOL every day at 00:15 UTC, horizon 1 day, entry window 12 h, gate needs ≥30 directional forecasts and ≥20 distinct cycle dates. Only forecasts made on/after 2026-09-26 count; earlier v1 forecasts are scored for information only.
- 2026-09-27: scoring bug fixed before any v2 forecast was scored: 'entered' forecasts were never re-evaluated; entry/horizon clock now starts at report write time (first full 1h candle after), horizon exit at the close of the candle containing the horizon end. Stuck forecasts re-scored from price history with unchanged rules.
- 2026-09-28: known limitation, not changed mid-sample: horizon exits can occur up to ~30 min before horizon end because the 00:05 UTC scoring uses the in-progress 1h candle; Freqtrade mirrors this via forecast_withdrawn. Unbiased in direction; applied identically to all v2 forecasts.
- 2026-09-28: CONTROL GROUP added before any verdict: always-long and always-short baselines on every v2 directional forecast (same instrument, window, stop/target distances, costs, scoring rules; entry at the open of the first full 1h candle after the report). New gate check: AI mean R per directional forecast (not_entered = 0) must beat the better of the two baselines by ≥ 0.10 R. Baselines are computed from price history for all v2 forecasts, including the ones already scored.

## Decision rules (written before the verdict)
- Verdict date: morning after the 20th distinct v2 cycle is scored (expected 2026-10-16).
- GATE PASSED → start Phase 2 (Freqtrade dry-run counts from that day, 1h entry rule unchanged); no prompt/model/universe changes until Phase 2 has its own verdict.
- GATE FAILED → protocol v2 closed as a confirmed negative result: timers disabled, repo archived with the final gate output and forecasts.csv. No re-run with another model, prompt or coin set under this hypothesis.
- If the AI fails only the control check (beats zero but not the best constant direction) → counts as FAILED: no edge beyond market direction.
- Operational outages (agent/data failures) do not extend the window; missing days simply reduce the sample. If fewer than 20 cycles exist by 2026-10-23, verdict = NOT DECIDABLE and the project stops unless a new protocol is pre-registered.
