# OKX Perpetual Swap Research Report: BTC-USDT-SWAP

```json
{"forecast": {"instrument": "BTC-USDT-SWAP", "date": "2026-09-26", "bias": "LONG", "confidence": "medium", "entry_low": 83800.0, "entry_high": 84100.0, "stop": 82750.0, "target1": 85950.0, "target2": 87200.0, "horizon_days": 1, "invalidation": ["1h candle close below 82,750 USDT breaking 1h EMA200 (82,915.7 USDT) and 4h EMA50 (82,955.0 USDT) confluence support", "Daily candle close below 20-day EMA at 81,027.2 USDT terminating macro bullish structure", "Derivatives regime flip to aggressive short expansion with surging OI and negative funding", "Sustained institutional spot Bitcoin ETF net daily outflows exceeding $500M"]}}
```

### Executive Summary
* **Directional Bias:** LONG (higher-low consolidation breakout aligned with daily/4-hour macro bull trend).
* **Confidence Level:** Medium (strong daily/4-hour structural alignment and complete derivatives reset; tempered by 1-hour EMA compression).
* **Execution Range:** Entry Zone: 83,800.0 – 84,100.0 USDT (Market / Pullback) | Hard Invalidation Stop: 82,750.0 USDT.
* **Profit Targets:** Target 1: 85,950.0 USDT (R:R 1.67 vs midpoint) | Target 2: 87,200.0 USDT (R:R 2.71 vs midpoint).
* **Top Downside Risk:** Decisive break below the dual-timeframe dynamic confluence floor at 82,915 – 82,955 USDT (1h EMA200 / 4h EMA50), risking a cascade toward the 20-day EMA (81,027.2 USDT).

---

## Part 0: Data Acquisition & Pipeline Environment

### Data Provenance & Methodology
* **Source:** OKX public REST market data endpoints and OKX Rubik trading-data endpoints processed via `scripts/pipeline.py`.
* **Execution Timestamp:** `2026-09-26T00:15:48+00:00` (UTC).
* **Primary Output Files:**
  * Summary metrics: [`out/summary.json`](file:///home/jetson/vibe-trading-okx-futures/out/summary.json)
  * Multi-timeframe OHLCV datasets: [`out/BTC-USDT-SWAP_1d.csv`](file:///home/jetson/vibe-trading-okx-futures/out/BTC-USDT-SWAP_1d.csv) (365 daily bars), [`out/BTC-USDT-SWAP_4h.csv`](file:///home/jetson/vibe-trading-okx-futures/out/BTC-USDT-SWAP_4h.csv) (2,190 4-hour bars), [`out/BTC-USDT-SWAP_1h.csv`](file:///home/jetson/vibe-trading-okx-futures/out/BTC-USDT-SWAP_1h.csv) (1,440 1-hour bars).
  * Derivatives metrics: [`out/funding.csv`](file:///home/jetson/vibe-trading-okx-futures/out/funding.csv) (287 settlement intervals spanning ~95 days), [`out/contract_stats.csv`](file:///home/jetson/vibe-trading-okx-futures/out/contract_stats.csv) (100 hourly snapshots of Open Interest, LSR, taker volume, and liquidations).
  * Graphical artifacts: Rendered and stored in [`reports/img/`](file:///home/jetson/vibe-trading-okx-futures/reports/img/) (`chart_1d.png`, `chart_4h.png`, `chart_1h.png`, `chart_derivatives.png`).

---

## Part 1: Contract & Market Structure

### 1. Facts (Data-Derived)
*Source: `summary.json` → `contract_specs`, `ticker`*

| Specification Field | Raw Value | Metric Interpretation |
| :--- | :--- | :--- |
| **Instrument ID (`instId`)** | `BTC-USDT-SWAP` | Linear perpetual swap margined and settled in USDT |
| **Underlying (`uly`)** | `BTC-USDT` | Bitcoin spot reference index basket |
| **Contract Value (`ctVal`)** | `0.01` | Each contract represents exactly 0.01 BTC |
| **Contract Value Currency (`ctValCcy`)** | `BTC` | Base currency is Bitcoin |
| **Contract Multiplier (`ctMult`)** | `1` | Linear payout multiplier |
| **Contract Type (`ctType`)** | `linear` | Direct USDT settlement |
| **Maximum Leverage (`lever`)** | `100` | Up to 100x account-level leverage permitted |
| **Tick Size (`tickSz`)** | `0.1` | Minimum price fluctuation is 0.1 USDT |
| **Lot Size (`lotSz`) / Min Size (`minSz`)** | `0.01` | Minimum order size is 0.01 contracts (= 0.0001 BTC) |
| **Max Limit Order Size (`maxLmtSz`)** | `100000000` | Maximum limit order size: 100,000,000 contracts |
| **Max Market Order Size (`maxMktSz`)** | `35000` | Maximum single market order: 35,000 contracts (= 350 BTC) |
| **Settlement Currency (`settleCcy`)** | `USDT` | Margin, PnL, and funding paid in USDT |
| **Trading State (`state`)** | `live` | Actively trading (listed 2019-11-12 11:16:48 UTC; `listTime`: `1573557408000`) |
| **Expiration Time (`expTime`)** | `""` (null / empty) | Perpetual instrument with no fixed expiry |
| **Funding Interval (`funding_interval_hours`)** | `8.0` | Settled every 8 hours (00:00, 08:00, 16:00 UTC) |
| **Ticker Last Price (`last`)** | `84039.3` | Last trade matched at 84,039.3 USDT |
| **Top of Book Depth** | Bid: `84039.2` (575.95 ct) / Ask: `84039.3` (559.97 ct) | Tightest possible 1-tick spread: 0.1 USDT (~0.00012%) |
| **24h Volume Base (`volCcy24h`)** | `77934.0969` BTC | 77,934.1 BTC traded in trailing 24 hours |
| **24h Volume Contracts (`vol24h`)** | `7793409.69` contracts | 24h Turnover: ~**$6,549,516,613 USDT** notional |
| **24h High / Low Range** | Low: `83118.0` / High: `85242.2` | 24h Absolute Range: 2,124.2 USDT (2.54%) |
| **Start of Day (SOD) Reference** | UTC 0: `84059.9` / UTC 8: `83760.0` | Intraday reference anchors |
| **Mark vs Index Price** | Mark: `84039.3` / Index: `84076.3` | Mark trades at a modest discount of -37.0 USDT (-0.0440%) |
| **Open Interest (`open_interest_latest`)** | `3116893207.6018` contracts | Total open interest: ~**$3,116,893,208 USDT** |

### 2. Interpretation & Liquidity Analysis
* **Execution Liquidity & Microstructure:** BTC-USDT-SWAP on OKX is an ultra-liquid tier-1 derivatives instrument. With over 7.79 million contracts (~$6.55 billion) in 24h volume and over 550 contracts (~5.5 BTC / $462,000) resting directly at the tightest 1-tick bid-ask spread (0.1 USDT), retail and institutional traders can execute standard positions (1–50 BTC) with negligible market impact and near-zero slippage.
* **Cost of Carry Analysis (24-Hour Horizon):**
  * **Trading Fee Model:** Baseline VIP0 fee schedule is 0.050% (5 bps) taker and 0.020% (2 bps) maker. A complete taker round-trip execution represents 0.100% (10 bps) in baseline friction.
  * **Funding Rates:**
    * Latest settled funding rate: **+0.001700%** per 8h (`summary.json` → `funding.latest_pct`).
    * 7-day mean funding rate: **+0.005945%** per 8h (= **+0.017836%** daily).
    * 30-day mean funding rate: **+0.005447%** per 8h (= **+0.016342%** daily, **5.965% APR** annualized).
  * **Long Position Carry Cost:** Long holders pay positive funding to shorts. Over a 24-hour holding horizon spanning 3 funding settlements (00:00, 08:00, 16:00 UTC), expected funding drag based on the 7-day mean is **+0.0178%** (~1.8 bps). When combined with round-trip taker fees (0.100%), total carrying drag for a long is ~**0.118%** (~11.8 bps). At current suppressed funding levels (+0.0017% per 8h), carry cost is virtually negligible at ~0.0051% daily (~0.5 bps).
  * **Short Position Carry Yield:** Short holders receive funding payments. Over 24 hours, shorts earn a modest positive carry of +0.0178% (7d mean), which offsets 17.8% of round-trip taker fees (or produces positive net yield if executed via limit maker orders).

---

## Part 2: Price Action & Technical Analysis

### Visual Multi-Timeframe Charts

![1D Chart](img/chart_1d.png)

![4H Chart](img/chart_4h.png)

![1H Chart](img/chart_1h.png)

### 1. Facts (Multi-Timeframe Metrics)
*Source: `summary.json` → `timeframes` & OHLCV CSV datasets*

| Indicator / Metric | Daily (1D) | 4-Hour (4H) | 1-Hour (1H) |
| :--- | :--- | :--- | :--- |
| **Last Close Price** | `84039.3` USDT | `84039.3` USDT | `84039.3` USDT |
| **7-Day / 30-Day Return** | +3.46% / +4.77% | +3.60% / +6.65% | +2.91% / +6.84% |
| **EMA 20** | `81027.2` USDT | `84191.1` USDT | `84038.3` USDT |
| **EMA 50** | `76720.4` USDT | `82955.0` USDT | `84220.1` USDT |
| **EMA 200** | `74122.2` USDT | `78510.5` USDT | `82915.7` USDT |
| **Trend Structure Classification** | **UP** (Price > EMA20 > EMA50 > EMA200) | **UP** (EMA50 > EMA200; Retracement holding) | **MIXED** (Hugging EMA20/50, firmly > EMA200) |
| **RSI 14** | `64.20` (Bullish expansion) | `50.45` (Neutral reset) | `48.88` (Neutral equilibrium) |
| **MACD Histogram** | `+284.28` (Positive momentum) | `-210.95` (Negative, contracting) | `+8.78` (Bullish crossover, positive) |
| **ATR 14 / ATR %** | 2,338.6 USDT / `2.78%` | 930.1 USDT / `1.11%` | 427.7 USDT / `0.51%` |
| **30-Day Realized Volatility (Ann.)** | `43.49%` | `35.02%` | `34.73%` |
| **Key Pivot Support Levels** | `83777.0`, `80602.4`, `76204.5`, `74896.6` | `83777.0`, `82812.5`, `80918.1`, `80602.4` | `83707.0`, `83680.3`, `83439.3`, `83118.0` |
| **Key Pivot Resistance Levels** | `87374.3`, `90574.0`, `94151.9`, `94569.9` | `87245.0`, `87374.3`, `88146.6`, `89183.2` | `84580.0`, `84638.3`, `84860.0`, `84931.3` |

### 2. Interpretation & Key Level Validation
* **Multi-Timeframe Trend Structure:**
  * **Macro Context (Daily):** The daily timeframe exhibits an unambiguous bull trend (`up`). Price is trading well above the ascending 20-day EMA (`81,027.2`), the 50-day EMA (`76,720.4`), and the 200-day EMA (`74,122.2`). The Golden Cross established in late August / early September continues to widen, while the daily MACD histogram remains firmly positive (`+284.28`). Daily RSI (`64.20`) reflects strong bullish control without reaching overbought exhaustion (>70).
  * **Intermediate Context (4-Hour):** The 4-hour trend structure is firmly bullish (`up`). The 4-hour EMA50 (`82,955.0`) sits more than 4,400 points above the 4-hour EMA200 (`78,510.5`). Following the rejection off the cycle high at 87,245.0 USDT on September 23, price retraced to establish a major swing low at 82,812.5 USDT on September 24 and a higher low at 83,118.0 USDT on September 25. Price is currently testing directly into the declining 4-hour EMA20 (`84,191.1`).
  * **Micro Execution Context (1-Hour):** The 1-hour structure is classified as `mixed` but exhibits constructive bottoming characteristics. Price closed at 84,039.3 USDT, reclaiming the 1-hour EMA20 (`84,038.3`) and consolidating just below the 1-hour EMA50 (`84,220.1`). Notably, the rising 1-hour EMA200 (`82,915.7`) has acted as an iron floor during all recent pullbacks.
* **Dual-Timeframe Dynamic Confluence Floor (82,812 – 82,955 USDT):**
  * There is a striking structural confluence guarding the downside:
    * **1-Hour EMA200:** `82,915.7` USDT
    * **4-Hour EMA50:** `82,955.0` USDT
    * **4-Hour / Daily Pivot Support:** `82,812.5` USDT
  * These key technical indicators converge into a high-conviction demand zone between **82,812 and 82,955 USDT**. As long as 1-hour and 4-hour candle closes remain above this confluence shelf, the broader bullish thesis remains intact.
* **Ascending Base & Higher Lows:**
  * Price action over the last 48 hours shows a clear progression of higher lows:
    * September 24 trough: `82,812.5` USDT (initial flush)
    * September 25 trough: `83,118.0` USDT (+305.5 USDT higher)
    * September 25 late session: `83,580.0` USDT (+462.0 USDT higher)
    * September 26 open: `83,733.8` → `84,039.3` USDT (+153.8 USDT higher)
  * This ascending stair-step structure demonstrates persistent dip-buying absorption at progressively higher price levels.
* **Momentum & Divergence Analysis:**
  * The 4-hour RSI has completed a full, healthy reset to the `50.45` neutral line (down from cycle extremes above 86), creating ample runway for the next leg higher.
  * The 1-hour MACD histogram has officially crossed positive (`+8.78`), confirming that hourly downward momentum has exhausted and buyers are initiating short-term expansion.
* **Volatility Regime & Compression:**
  * While daily volatility is normalized (ATR% = 2.78%, 2,338.6 USDT), 1-hour volatility has compressed significantly to **ATR% = 0.51%** (427.7 USDT). Historical precedent demonstrates that extreme hourly ATR compression during a higher-timeframe bull trend reliably precedes explosive directional expansion in the direction of the dominant macro trend.

---

## Part 3: Positioning & Derivatives Flow

### Derivatives Market Visual

![Derivatives Chart](img/chart_derivatives.png)

### 1. Facts (Data-Derived)
*Source: `summary.json` → `funding`, `positioning`, `basis` & `contract_stats.csv`*

| Metrics Category | Recorded Value | Context & Benchmark Comparison |
| :--- | :--- | :--- |
| **Latest Funding Rate** | `+0.001700%` per 8h | Subdued carry (0.17 bps per 8h); sits at **16.38th percentile** of 287 historical settlements |
| **7-Day Mean Funding** | `+0.005945%` per 8h | +0.017836% daily (+6.51% APR) |
| **30-Day Mean Funding** | `+0.005447%` per 8h | +0.016342% daily; **+5.965% APR** annualized |
| **30-Day Positive Funding Share** | `93.33%` | 268 of 287 intervals positive; persistent baseline spot demand |
| **Open Interest Latest** | `3,116,893,207.60` ct | Total value: ~**$3.117 Billion USDT**; near multi-day lows |
| **OI 24-Hour Change** | `-0.8345%` (-26.1M ct) | Steady deleveraging over trailing 24 hours |
| **Price Change Same Window** | `-0.6164%` | Mild contraction in price alongside open interest drop |
| **Positioning Regime** | `long unwind (price down, OI down)` | Orderly de-risking and liquidation of late longs; no aggressive short buildup |
| **OI Peak-to-Trough Flush** | `-10.10%` (-350.2M ct) | Fell from 3,467,134,049 ct (Sept 23) to 3,116,893,208 ct (Sept 26) |
| **Long/Short Account Ratio (`lsr_account_latest`)** | `1.29` | 56.3% accounts long vs 43.7% short (down from 1.34 peak) |
| **Taker Buy/Sell Ratio (`lsr_taker_latest`)** | `0.8675` | Taker sell volume ($35.4M) exceeded taker buy volume ($30.7M) |
| **24h Liquidations Sum** | Long: `423.81` ct / Short: `227.17` ct | Long liquidations outpaced shorts by **1.87 to 1** |
| **Mark-Index Basis** | `-0.0440%` (-4.40 bps) | Mark price trades 37.0 USDT below spot index |
| **Perp-Spot Basis (Latest / 30d Mean)** | `-0.0490%` / `-0.0436%` | Perps consistently trade at a 4.4 to 4.9 bps discount to spot index |

### 2. Interpretation & Flow Mechanics
* **Comprehensive Deleveraging & Positioning Health:**
  * When Bitcoin rallied to 87,245 USDT on September 22–23, open interest expanded to an overheated 3.467 billion contracts. Over the subsequent 72 hours, open interest shed **350.2 million contracts (-10.10%)**, bottoming at 3.117 billion contracts.
  * The positioning regime is officially classified as `long unwind (price down, OI down)`. This distinction is critical: the pullback was driven by the flushing of over-leveraged long speculators, rather than an aggressive institutional short accumulation (`price down, OI up`). The derivatives market has completely purged excess froth.
* **Funding Rate Collapse to 16th Percentile:**
  * Funding rates have dropped from elevated readings near the 0.010% cap to just **+0.001700%** per 8h. Sitting in the **16.38th percentile** of historical observations, holding long exposure carries virtually zero financing friction (~0.5 bps/day). This demonstrates that perpetual swap traders are cautious and under-positioned, leaving ample room for aggressive leverage re-expansion upon a breakout.
* **Absorption of Taker Selling:**
  * Over the trailing 24 hours, the taker volume ratio printed `0.8675`, indicating that aggressive taker sells dominated the order flow. Despite this selling pressure and over 423 contracts of long liquidations on the flush to 83,118 USDT, price absorbed the volume cleanly and stabilized above 84,000 USDT. Persistent absorption in the face of net taker selling is a hallmark of passive institutional limit accumulation.
* **Perpetual Basis Discount:**
  * The perpetual swap continues to trade at a modest discount to spot index (`-4.40 bps` Mark-Index, `-4.90 bps` Perp-Spot), mirroring the 30-day average discount of `-4.36 bps`.
  * The absence of a perp premium verifies that this market cycle is fundamentally driven by physical spot acquisition (e.g., regulated ETFs and corporate treasury flows) rather than synthetic offshore leverage.

---

## Part 4: Narrative, Catalysts & Cross-Market Context

### 1. Facts & Recent Fundamental Developments
*Sources: Financial media, institutional disclosures, regulatory releases*

* **Resurgence of Spot Bitcoin ETF Inflows:** In mid-to-late September 2026, U.S. regulated spot Bitcoin ETFs underwent a massive reversal in institutional demand. Following a six-day consecutive inflow streak totaling over **$2.8 billion**, highlighted by a record single-day inflow of approximately **$999 million on September 21**, spot Bitcoin ETF net flows for calendar year 2026 crossed decisively into net positive territory, erasing the multi-billion dollar outflow deficit accumulated earlier in the summer.
* **Federal Reserve Hawkish Rate Hike:** On September 16, 2026, the Federal Reserve (under Chair Kevin Warsh) delivered a unanimous 25 basis point rate hike, lifting the federal funds target range to **3.75%–4.00%** due to persistent inflationary prints. While robust U.S. PMI data pushed the 10-year Treasury yield toward 5% on September 24 (triggering a risk-off pullback across macro equities and crypto from $87k to $83k), Bitcoin exhibited resilience by absorbing the shock and consolidating above $84,000.
* **Treasury Liquidity Backstop:** The macro backdrop remains buoyed by the U.S. Treasury's regular bond buyback operations initiated in August 2026, which continue to inject baseline dollar liquidity into commercial banking channels.
* **Exchange Security Incident Contained:** In late September 2026, centralized exchange Bitget reported an unauthorized transfer incident totaling ~$351.6 million. Bitget promptly reaffirmed that all user funds were backed 1:1 by reserve protection funds, preventing any systemic contagion or destabilization in offshore derivatives markets.
* **Global Community & Developer Focus:** The week of September 24–27, 2026 coincided with major developer gatherings in Tokyo (ETHGlobal Tokyo 2026, Pragma Tokyo), maintaining strong engagement and development velocity across the broader digital asset ecosystem.

### 2. Cross-Market Beta & Catalyst Pipeline
* **Market Beta & Dominance:** Total crypto market capitalization trades firmly near **$3.0 Trillion**, with Bitcoin dominance holding above 58%. Capital concentration in Bitcoin remains elevated as institutional market participants prioritize the asset's regulatory clarity and spot ETF liquidity.
* **Near-Term Upside Catalysts:**
  * **Q4 Institutional Allocations (October 1+):** Approaching end-of-quarter portfolio rebalancing and the deployment of fresh Q4 mandate capital into spot Bitcoin ETFs.
  * **1-Hour Breakout Ignition:** A sustained 1-hour close above the 84,220 USDT EMA50 and 84,580 USDT resistance level would trigger technical CTA trend-following strategies, targeting the 24h high at 85,242.2 USDT and 85,950 USDT.
* **Near-Term Downside Risks:**
  * **Persistent Yield Pressure:** Further surges in U.S. 10-year yields above 5.0% on hot inflation data could extend broad-market risk asset deleveraging.
  * **Confluence Support Breakdown:** An hourly close below 82,750 USDT breaking the 1h EMA200 / 4h EMA50 confluence would open downside risk toward the 20-day EMA at 81,027.2 USDT.

---

## Part 5: Synthesis & Trade Plan

### Core Thesis
Bitcoin's higher-timeframe trend remains decisively bullish, backed by a daily Golden Cross and accelerating institutional spot ETF inflows that crossed net-positive for 2026 following a $2.8B buying streak. The 72-hour pullback from 87,245 to 83,118 USDT has successfully purged over 350 million contracts of open interest (-10.1%), collapsing funding rates to the 16th percentile (0.0017% per 8h) and leaving perpetuals trading at a 4.4 bps discount to spot. With the market printing a sequence of higher lows and tightly compressing hourly volatility (ATR% = 0.51%) directly above the dual-timeframe confluence floor at 82,915 – 82,955 USDT, asymmetric risk-to-reward strongly favors a long position targeting a 24-hour expansion back toward 85,950 USDT.

### Directional Bias & Conviction
* **Bias:** **LONG**
* **Confidence Level:** **Medium**
* **Primary Evidence Anchors:**
  1. *Complete Derivatives Froth Flush:* Open interest purged by 350.2M contracts (-10.10%), funding cooled to 0.001700% (16.38th percentile), and perps trading at a -4.4 bps discount to spot.
  2. *Higher-Low Price Action Above Confluence Floor:* Progressive higher lows (82,812 → 83,118 → 83,580 → 83,734 USDT) firmly defending the dual 1h EMA200 (82,915.7 USDT) and 4h EMA50 (82,955.0 USDT) support shelf.
  3. *Momentum Turning & Volatility Compression:* 1-hour MACD histogram crossed positive (+8.78), 4-hour RSI fully reset to neutral 50.45, and 1-hour ATR% compressed to 0.51%, setting up an impending volatility expansion.

---

### Actionable Trade Plan (24-Hour Horizon)

```
        TARGET 2: 87,200.0 USDT  [+3.87% / R:R 2.71]  (4H Cycle High / Major Resistance)
            ▲
            │
        TARGET 1: 85,950.0 USDT  [+2.38% / R:R 1.67]  (Prior Range Liquidity / Above 24h High)
            ▲
            │
  ┌──────────────────────────────────────────────────┐
  │    ENTRY ZONE: 83,800.0 – 84,100.0 USDT          │  (Current Market: 84,039.3 / Micro Consolidation)
  └──────────────────────────────────────────────────┘
            │
    === CONFLUENCE SHELF: 82,915.0 – 82,955.0 USDT ===  (1h EMA200: 82,915.7 + 4h EMA50: 82,955.0)
            │
        HARD STOP: 82,750.0 USDT  [-1.43% Risk]       (Invalidation below 82,812.5 Pivot Low)
```

#### 1. Execution Parameters
* **Entry Range:** **83,800.0 – 84,100.0 USDT** (immediate execution around current market price of `84,039.3` USDT, with limit bids scaling down toward 83,800.0 USDT).
* **Midpoint Reference Entry:** `83,950.0` USDT (Current Market: `84,039.3` USDT).
* **Invalidation Level (Hard Stop):** **82,750.0 USDT**.
  * *Technical Rationale:* Positioned 165 USDT below the 1-hour EMA200 (`82,915.7`), 205 USDT below the 4-hour EMA50 (`82,955.0`), and 62.5 USDT below the multi-day pivot swing low (`82,812.5`). A decisive 1-hour candle close below 82,750 USDT invalidates the ascending base and confirms a deeper mean-reversion move toward the 20-day EMA (`81,027.2`).
* **Profit Target 1:** **85,950.0 USDT** (test of pre-drop consolidation liquidity above the 24h high of 85,242.2 USDT).
  * *Reward:* +2,000.0 USDT (+2.38% from midpoint; +1,910.7 USDT / +2.27% from current price).
  * *Risk:* 1,200.0 USDT (-1.43% from midpoint; 1,289.3 USDT / -1.53% from current price).
  * *Reward-to-Risk Ratio:* **1.67 : 1** (comfortably exceeding the 1.5× threshold).
* **Profit Target 2:** **87,200.0 USDT** (retest of 4H cycle high / major pivot resistance at 87,245.0 USDT).
  * *Reward:* +3,250.0 USDT (+3.87% from midpoint).
  * *Risk:* 1,200.0 USDT (-1.43% from midpoint).
  * *Reward-to-Risk Ratio:* **2.71 : 1**.

#### 2. Position Sizing & Margin Management
* **Portfolio Risk Budget:** Risk exactly **1.0% of total trading equity** on this setup.
* **Position Sizing Formula:**
  $$\text{Position Size (BTC)} = \frac{\text{Equity} \times 0.010}{\text{Entry Price} - \text{Stop Price}} = \frac{\text{Equity} \times 0.010}{83,950 - 82,750} = \frac{\text{Equity} \times 0.010}{1,200}$$
  * *Numerical Example:* On a $100,000 portfolio equity base, risking $1,000 with a $1,200 stop distance dictates a position size of **0.833 BTC** (~83 contracts of BTC-USDT-SWAP, representing ~$70,000 notional value, or 0.70x portfolio leverage).
* **Leverage Setting:**
  * Recommended Account Leverage: **2x to 5x** isolated margin.
  * Maximum Permissible Leverage: **10x** (at 10x isolated leverage, estimated liquidation price is ~76,000 USDT, positioned far below the stop at 82,750 USDT and daily EMA50 at 76,720.4 USDT).

#### 3. Funding & Cost Check (24-Hour Holding Window)
* **Settlements in Window:** Exactly 3 funding settlements (00:00, 08:00, 16:00 UTC).
* **Expected Daily Carry Drain:** Using the 7-day mean funding rate of 0.005945% per 8h, cumulative funding drag over 24 hours is **0.01784%** (~1.8 bps). Using the latest print of 0.001700% per 8h, drag is only **0.00510%** (~0.5 bps).
* **Total Transaction & Carrying Friction:** Round-trip taker fee (0.100%) + 24h expected funding (0.018%) = **0.118%** (~11.8 bps).
* **Expectancy Preservation:** Target 1 delivers gross profit of +2.38% (238 bps). Total friction (11.8 bps) consumes only **4.96%** of Target 1 gains, leaving a net profit of **+2.26%**. Even under adverse funding scenarios, the net reward remains well above 1.5× the net risk.

---

### Invalidation & Exit Checklist
Immediately exit or close the position upon any of the following triggers:
1. **Technical Invalidation:** A 1-hour candle close below **82,750.0 USDT**, breaking the 1h EMA200 / 4h EMA50 confluence support.
2. **Macro Structure Invalidation:** A daily candle close below the 20-day EMA at **81,027.2 USDT**.
3. **Derivatives Aggression Flip:** An abrupt surge in open interest (>100M contracts) accompanied by negative funding rates and persistent taker selling (`lsr_taker` < 0.70), indicating aggressive institutional short positioning.
4. **Institutional Capital Outflow:** Multiple consecutive sessions of heavy U.S. spot Bitcoin ETF net outflows exceeding $500M.

---

### Confidence & Analytical Limitations
* **OKX Rubik Data Aggregation:** Open interest, long/short account ratio, and taker buy/sell volume metrics provided by OKX Rubik are aggregated per currency (BTC) across all OKX instruments (including coin-margined inverse contracts and dated futures), rather than isolated exclusively to `BTC-USDT-SWAP`.
* **Liquidation Order Truncation:** Public liquidation data reflects only the latest ~100 forced liquidation orders; aggregate market liquidation magnitude must be cross-verified through hourly open interest delta.
* **Spot ETF Reporting Lag:** Official daily spot ETF inflow/outflow figures are reported with an overnight settlement lag, requiring intraday technical price structure to act as the primary real-time proxy for institutional demand.
