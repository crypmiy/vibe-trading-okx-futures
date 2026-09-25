"""Freqtrade dry-run executor for vibe forecasts (Phase 2).

Reads signals/active.json (exported by scripts/forecast_log.py) every candle and
executes each LONG/SHORT thesis mechanically: enter when the 1h close is inside the
entry zone before entry_deadline, hard stop at `stop`, exit at `target1` or when
`expires_at` passes. Leverage 1×. Nothing here is a signal of its own.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pandas import DataFrame
from freqtrade.strategy import IStrategy, stoploss_from_absolute

SIGNALS = Path(__file__).resolve().parents[3] / "signals" / "active.json"


def _load() -> dict[str, dict]:
    try:
        data = json.loads(SIGNALS.read_text())
        return {s["pair"]: s for s in data.get("signals", [])}
    except Exception:  # noqa: BLE001
        return {}


class VibeForecastStrategy(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1h"
    can_short = True
    process_only_new_candles = True
    startup_candle_count = 0
    stoploss = -0.10                 # emergency cap; the real stop is set in custom_stoploss
    use_custom_stoploss = True
    minimal_roi = {"0": 10}          # exits are handled in custom_exit
    order_types = {"entry": "market", "exit": "market", "stoploss": "market", "stoploss_on_exchange": False}

    def leverage(self, pair, current_time, current_rate, proposed_leverage, max_leverage, entry_tag, side, **kwargs) -> float:
        return 1.0

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        s = _load().get(metadata["pair"])
        dataframe["enter_long"] = 0; dataframe["enter_short"] = 0
        if not s:
            return dataframe
        deadline = datetime.fromisoformat(s["entry_deadline"])
        lo, hi = sorted([s["entry_low"], s["entry_high"]])
        in_zone = (dataframe["close"] >= lo) & (dataframe["close"] <= hi) & (dataframe["date"] <= deadline)
        col = "enter_long" if s["side"] == "long" else "enter_short"
        dataframe.loc[in_zone, col] = 1
        dataframe.loc[in_zone, "enter_tag"] = s["forecast_id"]
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["exit_long"] = 0; dataframe["exit_short"] = 0
        return dataframe

    def custom_stoploss(self, pair, trade, current_time, current_rate, current_profit, after_fill, **kwargs) -> float | None:
        s = _load().get(pair)
        if not s or s["forecast_id"] != trade.enter_tag:
            return None
        return stoploss_from_absolute(s["stop"], current_rate, is_short=trade.is_short, leverage=trade.leverage)

    def custom_exit(self, pair, trade, current_time, current_rate, current_profit, **kwargs):
        s = _load().get(pair)
        if not s or s["forecast_id"] != trade.enter_tag:
            return "forecast_withdrawn"
        if current_time.astimezone(timezone.utc) >= datetime.fromisoformat(s["expires_at"]):
            return "horizon"
        if (not trade.is_short and current_rate >= s["target1"]) or (trade.is_short and current_rate <= s["target1"]):
            return "target1"
        return None
