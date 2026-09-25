"""Indicators, derivatives-positioning stats and charts for one OKX perpetual.

Pure pandas/numpy/matplotlib so it runs unchanged on a Colab VM or a Jetson venv.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402


# ---------- indicators ----------
def ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def macd(close: pd.Series, fast=12, slow=26, sig=9):
    line = ema(close, fast) - ema(close, slow)
    signal = ema(line, sig)
    return line, signal, line - signal


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    tr = pd.concat([df.high - df.low,
                    (df.high - df.close.shift()).abs(),
                    (df.low - df.close.shift()).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for n in (20, 50, 200):
        out[f"ema{n}"] = ema(out.close, n)
    out["rsi14"] = rsi(out.close)
    out["macd"], out["macd_signal"], out["macd_hist"] = macd(out.close)
    out["atr14"] = atr(out)
    out["atr_pct"] = out.atr14 / out.close * 100
    out["ret"] = out.close.pct_change()
    return out


def swing_levels(df: pd.DataFrame, lookback: int = 5, top_n: int = 4) -> dict:
    """Simple pivot highs/lows as candidate support/resistance."""
    hi, lo = df.high, df.low
    ph = hi[(hi == hi.rolling(2 * lookback + 1, center=True).max())].dropna()
    pl = lo[(lo == lo.rolling(2 * lookback + 1, center=True).min())].dropna()
    last = float(df.close.iloc[-1])
    res = sorted({round(float(v), 8) for v in ph if v > last})[:top_n]
    sup = sorted({round(float(v), 8) for v in pl if v < last}, reverse=True)[:top_n]
    return {"resistance": res, "support": sup}


# ---------- summaries ----------
def _f(v):
    try:
        v = float(v)
        return None if np.isnan(v) else v
    except (TypeError, ValueError):
        return None


def timeframe_summary(df: pd.DataFrame, interval: str, bars_per_day: float) -> dict:
    x = add_indicators(df)
    last = x.iloc[-1]
    n7 = int(round(7 * bars_per_day))
    n30 = int(round(30 * bars_per_day))
    rv = x.ret.rolling(n30).std().iloc[-1] * np.sqrt(365 * bars_per_day) * 100 if len(x) > n30 else None

    def pct(n):
        return _f((x.close.iloc[-1] / x.close.iloc[-1 - n] - 1) * 100) if len(x) > n else None

    if len(x) >= 200:
        trend = ("up" if last.close > last.ema50 > last.ema200
                 else "down" if last.close < last.ema50 < last.ema200 else "mixed")
    else:
        trend = "insufficient history for EMA200"
    return {
        "interval": interval,
        "bars": int(len(x)),
        "last_close": _f(last.close),
        "change_pct": {"7d": pct(n7), "30d": pct(n30)},
        "ema": {"20": _f(last.ema20), "50": _f(last.ema50), "200": _f(last.ema200) if len(x) >= 200 else None},
        "trend_structure": trend,
        "rsi14": _f(last.rsi14),
        "macd_hist": _f(last.macd_hist),
        "atr_pct": _f(last.atr_pct),
        "realized_vol_30d_annualized_pct": _f(rv),
        "levels": swing_levels(x),
    }


def funding_summary(f: pd.DataFrame, funding_interval_h: float) -> dict:
    if f.empty:
        return {}
    per_day = 24 / funding_interval_h
    r = f.funding_rate
    r7, r30 = r.tail(int(7 * per_day)), r.tail(int(30 * per_day))
    return {
        "samples": int(len(r)),
        "funding_interval_hours": funding_interval_h,
        "latest_pct": _f(r.iloc[-1] * 100),
        "mean_7d_pct": _f(r7.mean() * 100),
        "mean_30d_pct": _f(r30.mean() * 100),
        "annualized_30d_pct": _f(r30.mean() * per_day * 365 * 100),
        "percentile_of_latest_in_history": _f((r < r.iloc[-1]).mean() * 100),
        "share_positive_30d_pct": _f((r30 > 0).mean() * 100),
    }


def positioning_summary(cs: pd.DataFrame, price: pd.Series) -> dict:
    if cs.empty:
        return {}
    out: dict = {"samples_hourly": int(len(cs))}
    if "open_interest" in cs:
        oi = cs.open_interest
        n = min(24, len(oi) - 1)
        out["open_interest_latest"] = _f(oi.iloc[-1])
        out["oi_change_24h_pct"] = _f((oi.iloc[-1] / oi.iloc[-1 - n] - 1) * 100) if n > 0 else None
        p = price.reindex(cs.index, method="nearest")
        out["price_change_same_window_pct"] = _f((p.iloc[-1] / p.iloc[-1 - n] - 1) * 100) if n > 0 else None
        dp, doi = out["price_change_same_window_pct"], out["oi_change_24h_pct"]
        if dp is not None and doi is not None:
            out["oi_price_regime"] = {(True, True): "new longs (price up, OI up)",
                                      (True, False): "short covering (price up, OI down)",
                                      (False, True): "new shorts (price down, OI up)",
                                      (False, False): "long unwind (price down, OI down)"}[(dp > 0, doi > 0)]
    for k in ("lsr_taker", "lsr_account", "top_lsr_account", "top_lsr_size"):
        if k in cs:
            out[k + "_latest"] = _f(cs[k].iloc[-1])
    if "long_liq_size" in cs and "short_liq_size" in cs:
        out["liq_long_sum_24h"] = _f(cs.long_liq_size.tail(24).sum())
        out["liq_short_sum_24h"] = _f(cs.short_liq_size.tail(24).sum())
    return out


def basis_summary(tk: dict, perp_close: pd.Series, spot: pd.Series) -> dict:
    out: dict = {}
    mark, index = _f(tk.get("mark_price")), _f(tk.get("index_price"))
    if mark and index:
        out["mark_index_basis_pct"] = (mark / index - 1) * 100
    if not spot.empty:
        aligned = pd.concat([perp_close.rename("perp"), spot.rename("spot")], axis=1).dropna()
        if len(aligned):
            b = (aligned.perp / aligned.spot - 1) * 100
            out["perp_spot_basis_latest_pct"] = _f(b.iloc[-1])
            out["perp_spot_basis_mean_30d_pct"] = _f(b.tail(30 * 24).mean())
    return out


# ---------- charts ----------
def chart_price(df: pd.DataFrame, interval: str, contract: str, path: Path) -> None:
    x = add_indicators(df).tail(300)
    w = 0.8 * (x.index[1] - x.index[0])
    fig, ax = plt.subplots(4, 1, figsize=(12, 11), sharex=True,
                           gridspec_kw={"height_ratios": [3, 1, 1, 1]})
    ax[0].plot(x.index, x.close, lw=1, color="black", label="close")
    for n, c in ((20, "tab:orange"), (50, "tab:green"), (200, "tab:red")):
        ax[0].plot(x.index, x[f"ema{n}"], lw=0.9, color=c, label=f"EMA{n}")
    ax[0].set_title(f"{contract} perpetual — {interval}")
    ax[0].legend(loc="upper left", fontsize=8)
    ax[1].bar(x.index, x.quote_volume, width=w, color="grey"); ax[1].set_ylabel("quote vol")
    ax[2].plot(x.index, x.rsi14, lw=0.9)
    ax[2].axhline(70, ls="--", lw=0.6, color="red"); ax[2].axhline(30, ls="--", lw=0.6, color="green")
    ax[2].set_ylabel("RSI14")
    ax[3].bar(x.index, x.macd_hist, width=w, color=np.where(x.macd_hist >= 0, "green", "red"))
    ax[3].plot(x.index, x.macd, lw=0.8); ax[3].plot(x.index, x.macd_signal, lw=0.8)
    ax[3].set_ylabel("MACD")
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)


def chart_derivatives(funding: pd.DataFrame, cs: pd.DataFrame, price: pd.Series, contract: str, path: Path) -> None:
    fig, ax = plt.subplots(3, 1, figsize=(12, 9))
    if not funding.empty:
        f = funding.tail(270)
        ax[0].bar(f.index, f.funding_rate * 100, width=0.3, color=np.where(f.funding_rate >= 0, "green", "red"))
        ax[0].set_title(f"{contract} funding rate (%) per settlement")
    if not cs.empty and "open_interest" in cs:
        ax[1].plot(cs.index, cs.open_interest, color="tab:blue")
        ax[1].set_ylabel("OI (contracts)", color="tab:blue")
        ax2 = ax[1].twinx()
        ax2.plot(cs.index, price.reindex(cs.index, method="nearest"), color="black", lw=0.8)
        ax2.set_ylabel("price")
        ax[1].set_title("open interest vs price (hourly)")
    if not cs.empty and "long_liq_size" in cs:
        ax[2].bar(cs.index, cs.long_liq_size, width=0.03, color="red", label="long liq")
        ax[2].bar(cs.index, -cs.short_liq_size, width=0.03, color="green", label="short liq")
        ax[2].legend(fontsize=8); ax[2].set_title("liquidations (long above / short below)")
    fig.tight_layout(); fig.savefig(path, dpi=110); plt.close(fig)


def write_json(obj: dict, path: Path) -> None:
    path.write_text(json.dumps(obj, indent=2, default=str))
