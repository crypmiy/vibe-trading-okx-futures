"""Minimal OKX USDT-margined perpetual (SWAP) public-data client — no API key required.

Endpoints (OKX API v5, public, read-only):
  /public/instruments            contract specs (ctVal, lever, tickSz, state)
  /market/ticker                 last / 24h volume
  /public/mark-price             mark price
  /market/index-tickers          index price
  /public/funding-rate           current + next funding, funding interval
  /public/funding-rate-history   funding history (100/page, paginated)
  /market/history-candles        OHLCV (100/page, paginated)
  /public/open-interest          current OI
  /rubik/stat/contracts/open-interest-volume     hourly OI history
  /rubik/stat/contracts/long-short-account-ratio hourly long/short account ratio
  /rubik/stat/taker-volume                       hourly taker buy/sell volume
  /public/liquidation-orders     recent forced liquidations
  /market/index-candles          index (≈spot) closes for basis history
"""
from __future__ import annotations

import time
from typing import Any

import pandas as pd
import requests

BASE = "https://www.okx.com/api/v5"
UA = {"Accept": "application/json", "User-Agent": "vibe-trading-okx-futures/1.0"}

# OKX bar names; daily/weekly use the UTC variants so bars line up with funding/OI data
BAR = {"1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m", "1h": "1H", "2h": "2H", "4h": "4H",
       "6h": "6H", "12h": "12H", "1d": "1Dutc", "1w": "1Wutc"}
INTERVAL_SECONDS = {"1m": 60, "5m": 300, "15m": 900, "30m": 1800, "1h": 3600, "2h": 7200,
                    "4h": 14400, "6h": 21600, "12h": 43200, "1d": 86400, "1w": 604800}


def normalize_inst(name: str) -> str:
    """BTC → BTC-USDT-SWAP, BTC_USDT → BTC-USDT-SWAP, BTC-USDT-SWAP unchanged."""
    n = name.upper().replace("_", "-")
    if n.endswith("-SWAP"):
        return n
    if n.endswith("-USDT"):
        return n + "-SWAP"
    return n + "-USDT-SWAP"


def _get(path: str, params: dict[str, Any] | None = None, retries: int = 4) -> list:
    last: Exception | None = None
    for i in range(retries):
        try:
            r = requests.get(BASE + path, params=params, headers=UA, timeout=30)
            if r.status_code == 429:
                time.sleep(2 * (i + 1)); continue
            r.raise_for_status()
            j = r.json()
            if str(j.get("code")) != "0":
                raise RuntimeError(f"OKX {path}: code={j.get('code')} msg={j.get('msg')}")
            return j.get("data") or []
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(1.5 * (i + 1))
    raise RuntimeError(f"GET {path} failed after {retries} tries: {last}")


def _safe(fn, *a, **k):
    try:
        return fn(*a, **k)
    except Exception as e:  # noqa: BLE001
        print(f"[okx] optional call {fn.__name__} failed: {e}", flush=True)
        return pd.DataFrame() if fn.__name__ not in ("ticker", "contract_info") else {}


def _ms(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s.astype("int64"), unit="ms", utc=True)


def contract_info(inst: str) -> dict:
    d = _get("/public/instruments", {"instType": "SWAP", "instId": inst})
    if not d:
        raise RuntimeError(f"instrument {inst} not found on OKX SWAP")
    return d[0]


def ticker(inst: str) -> dict:
    t = (_get("/market/ticker", {"instId": inst}) or [{}])[0]
    mark = (_get("/public/mark-price", {"instType": "SWAP", "instId": inst}) or [{}])[0]
    idx = (_get("/market/index-tickers", {"instId": inst.replace("-SWAP", "")}) or [{}])[0]
    fr = (_get("/public/funding-rate", {"instId": inst}) or [{}])[0]
    t["mark_price"] = mark.get("markPx"); t["index_price"] = idx.get("idxPx")
    t["funding_rate"] = fr.get("fundingRate"); t["next_funding_rate"] = fr.get("nextFundingRate")
    t["funding_time"] = fr.get("fundingTime"); t["next_funding_time"] = fr.get("nextFundingTime")
    return t


def funding_interval_hours(tk: dict) -> float:
    try:
        return (int(tk["next_funding_time"]) - int(tk["funding_time"])) / 3_600_000
    except (KeyError, TypeError, ValueError):
        return 8.0


def candles(inst: str, interval: str, days: int) -> pd.DataFrame:
    """OHLCV back `days`, newest→oldest pagination with `after` (100 rows/call)."""
    bar = BAR[interval]
    start_ms = int((time.time() - days * 86400) * 1000)
    rows: list[list] = []
    after: str | None = None
    while True:
        p = {"instId": inst, "bar": bar, "limit": "100"}
        if after:
            p["after"] = after
        data = _get("/market/history-candles", p)
        if not data:
            break
        rows.extend(data)
        oldest = int(data[-1][0])
        if oldest <= start_ms or len(data) < 100:
            break
        after = str(oldest)
        time.sleep(0.12)
    if not rows:
        return pd.DataFrame()
    # [ts, o, h, l, c, vol(contracts), volCcy(base), volCcyQuote(quote), confirm]
    df = pd.DataFrame(rows).iloc[:, :9]
    df.columns = ["time", "open", "high", "low", "close", "volume_contracts", "base_volume", "quote_volume", "confirm"]
    for c in ["open", "high", "low", "close", "volume_contracts", "base_volume", "quote_volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["time"] = _ms(df["time"])
    df = df.drop_duplicates("time").sort_values("time").set_index("time")
    df = df[df.index >= pd.Timestamp(start_ms, unit="ms", tz="UTC")]
    return df[["open", "high", "low", "close", "volume_contracts", "quote_volume"]]


def funding_history(inst: str, limit: int = 1000) -> pd.DataFrame:
    rows: list[dict] = []
    after: str | None = None
    while len(rows) < limit:
        p = {"instId": inst, "limit": "100"}
        if after:
            p["after"] = after
        data = _get("/public/funding-rate-history", p)
        if not data:
            break
        rows.extend(data)
        if len(data) < 100:
            break
        after = data[-1]["fundingTime"]
        time.sleep(0.12)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    out = pd.DataFrame({"time": _ms(df["fundingTime"]),
                        "funding_rate": pd.to_numeric(df["fundingRate"], errors="coerce")})
    return out.drop_duplicates("time").sort_values("time").set_index("time")


def contract_stats(inst: str, interval: str = "1h", limit: int = 100) -> pd.DataFrame:
    """Hourly OI, long/short account ratio, taker buy/sell ratio (Rubik trading-data endpoints).

    Columns are normalized to the names analyze.py expects:
      open_interest, lsr_account, lsr_taker
    """
    ccy = inst.split("-")[0]
    period = "1H" if interval == "1h" else "1D"
    parts: list[pd.DataFrame] = []
    oi = _get("/rubik/stat/contracts/open-interest-volume", {"ccy": ccy, "period": period})
    if oi:
        d = pd.DataFrame(oi, columns=["time", "open_interest", "volume"])
        parts.append(d.assign(time=_ms(d["time"])).set_index("time")[["open_interest"]])
    lsr = _get("/rubik/stat/contracts/long-short-account-ratio", {"ccy": ccy, "period": period})
    if lsr:
        d = pd.DataFrame(lsr, columns=["time", "lsr_account"])
        parts.append(d.assign(time=_ms(d["time"])).set_index("time"))
    tv = _get("/rubik/stat/taker-volume", {"ccy": ccy, "instType": "CONTRACTS", "period": period})
    if tv:
        d = pd.DataFrame(tv, columns=["time", "taker_sell", "taker_buy"])
        d = d.assign(time=_ms(d["time"])).set_index("time")
        d = d.apply(pd.to_numeric, errors="coerce")
        d["lsr_taker"] = d.taker_buy / d.taker_sell.replace(0, float("nan"))
        parts.append(d[["taker_buy", "taker_sell", "lsr_taker"]])
    if not parts:
        return pd.DataFrame()
    df = pd.concat(parts, axis=1).apply(pd.to_numeric, errors="coerce").sort_index()
    return df.tail(limit)


def liquidations(inst: str) -> pd.DataFrame:
    """Recent forced liquidations, aggregated hourly into long_liq_size / short_liq_size (contracts)."""
    uly = inst.replace("-SWAP", "")
    data = _get("/public/liquidation-orders", {"instType": "SWAP", "uly": uly, "state": "filled", "limit": "100"})
    rows = []
    for item in data:
        if item.get("instId", inst) != inst:
            continue
        for d in item.get("details", []):
            rows.append({"time": int(d["ts"]), "side": d.get("posSide") or d.get("side"),
                         "sz": float(d.get("sz", 0)), "px": float(d.get("bkPx", 0))})
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df["time"] = _ms(df["time"]).dt.floor("h")
    long_ = df[df.side.isin(["long", "sell"])].groupby("time").sz.sum().rename("long_liq_size")
    short = df[df.side.isin(["short", "buy"])].groupby("time").sz.sum().rename("short_liq_size")
    return pd.concat([long_, short], axis=1).fillna(0).sort_index()


def spot_close(inst: str, interval: str, days: int) -> pd.Series:
    """Index closes (OKX index ≈ spot basket) for perp–index basis history."""
    idx = inst.replace("-SWAP", "")
    bar = BAR[interval]
    start_ms = int((time.time() - days * 86400) * 1000)
    rows: list[list] = []
    after: str | None = None
    try:
        while True:
            p = {"instId": idx, "bar": bar, "limit": "100"}
            if after:
                p["after"] = after
            data = _get("/market/history-index-candles", p)
            if not data:
                break
            rows.extend(data)
            if int(data[-1][0]) <= start_ms or len(data) < 100:
                break
            after = data[-1][0]
            time.sleep(0.12)
    except Exception:  # noqa: BLE001
        return pd.Series(dtype=float)
    if not rows:
        return pd.Series(dtype=float)
    s = pd.Series({pd.Timestamp(int(r[0]), unit="ms", tz="UTC"): float(r[4]) for r in rows})
    return s.sort_index()
