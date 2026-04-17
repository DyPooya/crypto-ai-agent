# Trade Engine — REST Analysis API

## Server

| Environment | Host | Port | Base URL |
|-------------|------|------|----------|
| Production | `193.36.85.229` | `8080` | `http://193.36.85.229:8080/api/analysis` |

All endpoints:
- Return `application/json`
- Require no authentication (same as existing endpoints)
- Do **not** send Telegram notifications — results are returned directly to the caller
- Produce structured logs at `INFO` level for each request
- Exception: `/catalysts` **does** send a Telegram alert to `DART_SIGNALS` when an upstream API fails or returns an unexpected schema

---

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/analysis/orderbook` | Order-book wall analysis for a coin |
| GET | `/api/analysis/indicators` | CVD · Open Interest · OB imbalance for a coin |
| GET | `/api/analysis/backtest` | Candle-validation backtest for a single coin |
| GET | `/api/analysis/backtest/top` | Backtest all supported coins and return top-10 most profitable |
| GET | `/api/analysis/trend` | Higher-timeframe EMA trend state (EMA7 / EMA25 / EMA99) for a coin |
| GET | `/api/analysis/trend/multi` | EMA trend state for 15min + 1h + 4h in a single call |
| GET | `/api/analysis/dominance-matrix` | BTC dominance capital-rotation matrix — pre-computed direction bias for a coin |
| GET | `/api/analysis/catalysts` | Aggregated macro events (Finnhub) + token catalysts (CoinMarketCal) within a time window |
| GET | `/api/analysis/journal` | Manual trade-journal entries with aggregate P&L stats and real-time unrealized PnL for open trades |
| GET | `/api/analysis/positions` | Engine-generated exchange positions (AI signal results) with aggregate WIN/LOSS/OPEN counters |

---

## 1. Order Book Walls

```
GET /api/analysis/orderbook
```

Returns the support and resistance walls nearest to the current (or supplied) price.

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `symbol` | string | Yes | — | Coin base symbol (see [Supported Coins](#supported-coins)) |
| `exchange` | string | No | `bitunix` | Exchange to query. One of: `binance` · `bitunix` · `hyperliquid` · `dydx` |
| `refPrice` | double | No | `0` | Custom reference price in USDT. Pass `0` to use the live mid-price. |

### Example Request

```
GET /api/analysis/orderbook?symbol=BTC&exchange=binance&refPrice=95000
```

### Example Response

```json
{
  "symbol": "BTC",
  "exchange": "binance",
  "livePrice": 95143.2500,
  "refPrice": 95000.0000,
  "obImbalanceRatio": 1.342,
  "obSignal": "Bullish pressure",
  "resistanceWalls": [
    { "price": 97000.0000, "volume": 45.23, "strengthTag": "2xl", "distancePct": 2.11 },
    { "price": 96400.0000, "volume": 31.10, "strengthTag": "xl",  "distancePct": 1.47 },
    { "price": 95800.0000, "volume": 18.45, "strengthTag": "m",   "distancePct": 0.84 }
  ],
  "supportWalls": [
    { "price": 94600.0000, "volume": 52.87, "strengthTag": "3xl", "distancePct": -0.42 },
    { "price": 94200.0000, "volume": 24.11, "strengthTag": "l",   "distancePct": -0.84 }
  ],
  "avgResistanceVolume": 25.10,
  "avgSupportVolume": 30.40
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Coin base symbol in uppercase |
| `exchange` | string | Exchange that was queried |
| `livePrice` | double | Mid-price from the live order book snapshot (best bid + best ask) / 2 |
| `refPrice` | double | Reference price used for wall proximity filtering. Equals `livePrice` when no custom price was supplied. |
| `obImbalanceRatio` | double \| null | 15-min rolling average bid-volume / ask-volume ratio. Only present for `binance`. `null` while the cache warms up (~2 min after server start). |
| `obSignal` | string \| null | Human-readable label for `obImbalanceRatio`. See thresholds below. `null` for non-Binance exchanges. |
| `resistanceWalls` | array | Ask-side wall levels above `refPrice`, ordered **farthest first** (highest price at top) |
| `supportWalls` | array | Bid-side wall levels below `refPrice`, ordered **nearest first** (highest price at top) |
| `avgResistanceVolume` | double | Average binned volume across all resistance walls inside the ±6% window |
| `avgSupportVolume` | double | Average binned volume across all support walls inside the ±6% window |

#### Wall Level Object

| Field | Type | Description |
|-------|------|-------------|
| `price` | double | Wall price in USDT |
| `volume` | double | Aggregated order volume at this price bin |
| `strengthTag` | string | Relative strength label based on `volume / sideAverage` ratio |
| `distancePct` | double | Distance from `refPrice` in percent. **Negative = support (below ref), Positive = resistance (above ref).** |

#### Strength Tag Reference

| Tag | volume / sideAvg | Meaning |
|-----|-----------------|---------|
| `xs` | < 0.5 | Very weak |
| `s` | 0.5 – 1.0 | Weak |
| `m` | 1.0 – 2.0 | Moderate |
| `l` | 2.0 – 4.0 | Large |
| `xl` | 4.0 – 7.0 | Very large |
| `2xl` | 7.0 – 12.0 | Significant wall |
| `3xl` | 12.0 – 20.0 | Strong wall |
| `4xl` | ≥ 20.0 | Extreme wall |

#### OB Imbalance Signal Thresholds (Binance only)

| `obImbalanceRatio` | `obSignal` |
|--------------------|------------|
| > 1.20 | `Bullish pressure` |
| 0.80 – 1.20 | `Neutral zone` |
| < 0.80 | `Bearish pressure` |
| null (cache cold) | `Warming up` |

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 404 | Exchange returned an empty order book snapshot for this coin |

---

## 2. Market Indicators

```
GET /api/analysis/indicators
```

Returns four Binance Futures market indicators for a coin — equivalent to the `/indicators` Telegram command. Data source is always **Binance Futures**.

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `symbol` | string | Yes | Coin base symbol (see [Supported Coins](#supported-coins)) |

### Example Request

```
GET /api/analysis/indicators?symbol=ETH
```

### Example Response

```json
{
  "symbol": "ETH",
  "source": "Binance Futures",
  "cvdValue": -1243.87,
  "cvdSignal": "Bearish (net selling)",
  "cvdPeriod": 5,
  "oiChangePct": 0.234,
  "oiSignal": "Rising (new positions)",
  "obImbalanceRatio": 0.912,
  "obSignal": "Neutral zone",
  "fundingRate": 0.000235,
  "fundingRateSignal": "Long-biased — caution on longs"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Coin base symbol in uppercase |
| `source` | string | Always `"Binance Futures"` |
| `cvdValue` | double | Cumulative Volume Delta over the last `cvdPeriod` × 15-min candles. **Positive = net buying pressure, Negative = net selling pressure.** |
| `cvdSignal` | string | `"Bullish (net buying)"` · `"Bearish (net selling)"` · `"Neutral"` |
| `cvdPeriod` | int | Number of 15-min candles used (always `5`) |
| `oiChangePct` | double \| null | Open Interest percentage change over the last 15 min. `null` if the Binance OI API is unreachable. |
| `oiSignal` | string \| null | `"Rising (new positions)"` · `"Falling (closing)"` · `null` when `oiChangePct` is unavailable |
| `obImbalanceRatio` | double \| null | 15-min rolling average of (bid volume / ask volume). `null` while the in-memory cache warms up (~2 min after server start). |
| `obSignal` | string \| null | `"Bullish pressure"` · `"Neutral zone"` · `"Bearish pressure"` · `"Warming up"` |
| `fundingRate` | double \| null | Current perpetual funding rate from Binance Futures (`/fapi/v1/premiumIndex`). **Positive = longs paying shorts (crowded long side). Negative = shorts paying longs (crowded short side).** `null` if the API is unreachable. |
| `fundingRateSignal` | string \| null | Human-readable crowd positioning label. See thresholds below. `null` when `fundingRate` is unavailable. |

#### Funding Rate Signal Thresholds

| `fundingRate` | `fundingRateSignal` |
|---------------|---------------------|
| > +0.0005 (+0.05%) | `Crowded LONG — high squeeze risk` |
| +0.0001 to +0.0005 | `Long-biased — caution on longs` |
| −0.0001 to +0.0001 | `Neutral` |
| −0.0005 to −0.0001 | `Short-biased — caution on shorts` |
| < −0.0005 (−0.05%) | `Crowded SHORT — high squeeze risk` |

> **Note:** Binance Futures settles funding every 8 hours (00:00 · 08:00 · 16:00 UTC). The rate is constant between settlements, so `fundingRate` reflects the **current period's fixed rate** — not a rolling average.

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Always returned; fields that are unavailable are `null` in the payload |

---

## 3. Backtest — Single Coin

```
GET /api/analysis/backtest
```

Runs the candle-validation backtest for one coin and returns detailed win/loss statistics per R/R ratio and direction.

Uses the same production signal conditions as the live trading engine:
- EMA(7) and EMA(25) positioning
- Candle anatomy (body ratio, shadow ratio, size constraints)
- 300-candle EMA warm-up before any signal is tested

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `symbol` | string | Yes | — | Coin base symbol |
| `timeframe` | string | Yes | — | Candle interval: `1min` · `5min` · `15min` · `30min` · `1h` · `4h` · `1day` |
| `candleLimit` | int | No | `1500` | Total candles to fetch. Range: 1–1500. The first 300 are used for warm-up. |

### Example Request

```
GET /api/analysis/backtest?symbol=BTC&timeframe=15min&candleLimit=1500
```

### Example Response

```json
{
  "symbol": "BTC",
  "timeframe": "15min",
  "totalCandles": 1500,
  "analysedCandles": 1200,
  "warmupCandles": 300,
  "longSignalCount": 87,
  "shortSignalCount": 92,
  "periodStart": "2025-02-01 10:30",
  "periodEnd": "2025-02-15 23:45",
  "longByRR": {
    "1:3": { "wins": 45, "losses": 18, "unresolved": 24, "winRate": 71.4 },
    "1:5": { "wins": 32, "losses": 28, "unresolved": 27, "winRate": 53.3 },
    "1:7": { "wins": 21, "losses": 35, "unresolved": 31, "winRate": 37.5 },
    "1:9": { "wins": 15, "losses": 42, "unresolved": 30, "winRate": 26.3 }
  },
  "shortByRR": {
    "1:3": { "wins": 48, "losses": 22, "unresolved": 22, "winRate": 68.6 },
    "1:5": { "wins": 35, "losses": 30, "unresolved": 27, "winRate": 53.8 },
    "1:7": { "wins": 24, "losses": 38, "unresolved": 30, "winRate": 38.7 },
    "1:9": { "wins": 18, "losses": 45, "unresolved": 29, "winRate": 28.6 }
  },
  "bestRR": "1:3",
  "bestRRScore": 71.4
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Coin base symbol |
| `timeframe` | string | Candle interval used |
| `totalCandles` | int | Total candles fetched (includes warm-up) |
| `analysedCandles` | int | `totalCandles - 300` — candles actually tested for signals |
| `warmupCandles` | int | Always `300` — consumed for EMA(7/25) initialisation |
| `longSignalCount` | int | Total LONG signals found across the analysed window |
| `shortSignalCount` | int | Total SHORT signals found across the analysed window |
| `periodStart` | string | Timestamp of the first analysed candle (`yyyy-MM-dd HH:mm`) |
| `periodEnd` | string | Timestamp of the last analysed candle (`yyyy-MM-dd HH:mm`) |
| `longByRR` | object | LONG stats for each R/R ratio. Keys: `"1:3"` `"1:5"` `"1:7"` `"1:9"` |
| `shortByRR` | object | SHORT stats for each R/R ratio |
| `bestRR` | string | The R/R key with the highest combined score (`winRate × ratio`) |
| `bestRRScore` | double | Score of the best R/R |

#### R/R Stats Object

| Field | Type | Description |
|-------|------|-------------|
| `wins` | int | Trades where price reached take-profit before stop-loss |
| `losses` | int | Trades where price reached stop-loss before take-profit |
| `unresolved` | int | Signals where neither TP nor SL was hit within the remaining candles |
| `winRate` | double | `wins / (wins + losses) × 100`. `0` if no resolved trades. |

#### Stop-loss / Take-profit Calculation

| Direction | Stop-loss | Take-profit |
|-----------|-----------|-------------|
| LONG | `lowestPrice × 0.996` | `entry + R × (entry - SL)` |
| SHORT | `highestPrice × 1.004` | `entry - R × (SL - entry)` |

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 404 | No candle data available for this coin/timeframe |

---

## 4. Backtest — Top Profitable (All Coins)

```
GET /api/analysis/backtest/top
```

Runs the backtest across **all supported coins** and returns the top-10 most profitable `(coin, direction, R/R)` combinations, ranked by simulated final capital.

> This endpoint runs the full backtest pipeline for every supported coin. Expect response times of **30–120 seconds** depending on the candle limit and number of coins.

### Capital Simulation Model

| Parameter | Value |
|-----------|-------|
| Starting capital | $100 |
| Risk per trade | $10 (10% of starting capital) |
| Profit formula | `wins × ($10 × R) − losses × $10` |
| Final capital | `$100 + profit` |

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `timeframe` | string | Yes | — | Candle interval: `1min` · `5min` · `15min` · `30min` · `1h` · `4h` · `1day` |
| `candleLimit` | int | No | `1500` | Candle count per coin (1–1500) |

### Example Request

```
GET /api/analysis/backtest/top?timeframe=15min&candleLimit=1500
```

### Example Response

```json
{
  "timeframe": "15min",
  "candleLimit": 1500,
  "startCapital": 100.0,
  "riskPerTrade": 10.0,
  "top10": [
    {
      "rank": 1,
      "symbol": "SOL",
      "direction": "LONG",
      "rr": "1:3",
      "finalCapital": 340.0,
      "profit": 240.0,
      "wins": 28,
      "losses": 4,
      "winRate": 87.5
    },
    {
      "rank": 2,
      "symbol": "BTC",
      "direction": "LONG",
      "rr": "1:5",
      "finalCapital": 290.0,
      "profit": 190.0,
      "wins": 15,
      "losses": 3,
      "winRate": 83.3
    }
  ]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `timeframe` | string | Candle interval used for all coins |
| `candleLimit` | int | Candle count used (capped at 1500) |
| `startCapital` | double | Simulation starting capital (always `100.0`) |
| `riskPerTrade` | double | Fixed risk per trade in USD (always `10.0`) |
| `top10` | array | Up to 10 ranked entries, most profitable first |

#### Top Entry Object

| Field | Type | Description |
|-------|------|-------------|
| `rank` | int | Position in the ranking (1 = most profitable) |
| `symbol` | string | Coin base symbol |
| `direction` | string | `"LONG"` or `"SHORT"` |
| `rr` | string | R/R ratio (e.g. `"1:3"`) |
| `finalCapital` | double | Simulated capital after all resolved trades |
| `profit` | double | `finalCapital - 100`. Positive = net profit, negative = net loss. |
| `wins` | int | Resolved winning trades |
| `losses` | int | Resolved losing trades |
| `winRate` | double | `wins / (wins + losses) × 100` |

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Always returned; `top10` may be empty if no coin had sufficient candle data |

---

## 5. Trend State

```
GET /api/analysis/trend
```

Returns the current EMA-stack trend state for a coin on any supported timeframe. Candles are fetched from the external price-service API (up to 1500) to maximise EMA-99 accuracy.

**Trend bias is determined entirely from the EMA7 / EMA25 / EMA99 ordering — live price does not affect it.**

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `symbol` | string | Yes | — | Coin base symbol (see [Supported Coins](#supported-coins)) |
| `timeframe` | string | Yes | — | Candle interval: `1min` · `5min` · `15min` · `30min` · `1h` · `4h` · `1day` |
| `lookback` | int | No | `10` | Number of recent candles used for slope calculation and alignment counting |

### Example Request

```
GET /api/analysis/trend?symbol=LDO&timeframe=1h&lookback=10
```

### Example Response

```json
{
  "symbol": "LDO",
  "timeframe": "1h",
  "currentPrice": 0.372750,
  "ema7": 0.381200,
  "ema25": 0.369100,
  "ema99": 0.355400,
  "ema7AboveEma25": true,
  "ema25AboveEma99": true,
  "ema7Slope": "falling",
  "ema25Slope": "rising",
  "ema99Slope": "rising",
  "alignedCandles": 7,
  "lookback": 10,
  "trendBias": "BULLISH"
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Coin base symbol in uppercase |
| `timeframe` | string | Candle interval used |
| `currentPrice` | double | Close price of the most recent candle (informational only — not used in trend bias) |
| `ema7` | double | EMA(7) value at the most recent candle |
| `ema25` | double | EMA(25) value at the most recent candle |
| `ema99` | double | EMA(99) value at the most recent candle |
| `ema7AboveEma25` | boolean | `true` when EMA7 > EMA25 |
| `ema25AboveEma99` | boolean | `true` when EMA25 > EMA99 |
| `ema7Slope` | string | Direction of EMA7 over the last `lookback` candles: `"rising"` · `"falling"` · `"flat"` |
| `ema25Slope` | string | Direction of EMA25 over the last `lookback` candles |
| `ema99Slope` | string | Direction of EMA99 over the last `lookback` candles |
| `alignedCandles` | int | Number of the last `lookback` candles where the EMA stack had the same ordering as the current `trendBias` |
| `lookback` | int | Lookback window used for slope and alignment (echoes the request parameter) |
| `trendBias` | string | EMA stack ordering label — see table below |

### Trend Bias Values

Trend bias expresses the **exact ordering of all three EMAs** as a range expression. Only the fully stacked cases are named — all others show the mathematical inequality:

| `trendBias` | EMA ordering | Interpretation |
|-------------|-------------|----------------|
| `BULLISH` | EMA7 > EMA25 > EMA99 | Full bull stack — all EMAs aligned upward |
| `BEARISH` | EMA7 < EMA25 < EMA99 | Full bear stack — all EMAs aligned downward |
| `EMA25 < EMA7 < EMA99` | EMA25 < EMA7 < EMA99 | EMA7 crossed above EMA25 but still below EMA99 — early bullish recovery |
| `EMA99 < EMA7 < EMA25` | EMA99 < EMA7 < EMA25 | EMA7 fell below EMA25 but still above EMA99 — early bearish weakening |
| `EMA7 < EMA99 < EMA25` | EMA7 < EMA99 < EMA25 | EMA7 deeply below both — deep bearish transition |
| `EMA25 < EMA99 < EMA7` | EMA25 < EMA99 < EMA7 | EMA7 above both but EMA25 not yet above EMA99 — deep bullish transition |

> **Slope threshold:** A change of less than 0.01% over `lookback` candles is reported as `"flat"` to filter EMA noise.

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 404 | Insufficient candle data for this coin/timeframe (need at least EMA99 period + lookback candles) |

---

## 6. Trend State — Multi-Timeframe

```
GET /api/analysis/trend/multi
```

Returns the EMA-stack trend state for **15min, 1h, and 4h** in a single call. Equivalent to calling `/trend` three times, but more efficient for the agent pipeline.

Each timeframe is computed independently from 1500 candles. A timeframe field is `null` when insufficient candle data is available for that interval.

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `symbol` | string | Yes | — | Coin base symbol (see [Supported Coins](#supported-coins)) |
| `lookback` | int | No | `10` | Number of recent candles used for slope calculation and alignment counting (applied to all three timeframes) |

### Example Request

```
GET /api/analysis/trend/multi?symbol=SOL&lookback=10
```

### Example Response

```json
{
  "symbol": "SOL",
  "lookback": 10,
  "15min": {
    "symbol": "SOL",
    "timeframe": "15min",
    "currentPrice": 142.850,
    "ema7": 143.210,
    "ema25": 141.880,
    "ema99": 139.450,
    "ema7AboveEma25": true,
    "ema25AboveEma99": true,
    "ema7Slope": "rising",
    "ema25Slope": "rising",
    "ema99Slope": "rising",
    "alignedCandles": 8,
    "lookback": 10,
    "trendBias": "BULLISH"
  },
  "1h": {
    "symbol": "SOL",
    "timeframe": "1h",
    "currentPrice": 142.850,
    "ema7": 141.600,
    "ema25": 143.200,
    "ema99": 138.900,
    "ema7AboveEma25": false,
    "ema25AboveEma99": true,
    "ema7Slope": "falling",
    "ema25Slope": "flat",
    "ema99Slope": "rising",
    "alignedCandles": 3,
    "lookback": 10,
    "trendBias": "EMA99 < EMA7 < EMA25"
  },
  "4h": {
    "symbol": "SOL",
    "timeframe": "4h",
    "currentPrice": 142.850,
    "ema7": 144.100,
    "ema25": 141.300,
    "ema99": 137.200,
    "ema7AboveEma25": true,
    "ema25AboveEma99": true,
    "ema7Slope": "rising",
    "ema25Slope": "rising",
    "ema99Slope": "rising",
    "alignedCandles": 9,
    "lookback": 10,
    "trendBias": "BULLISH"
  }
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `symbol` | string | Coin base symbol in uppercase |
| `lookback` | int | Lookback window echoed from the request |
| `15min` | object \| null | Full `TrendStateApiResponse` for the 15-minute timeframe. `null` if insufficient candle data. |
| `1h` | object \| null | Full `TrendStateApiResponse` for the 1-hour timeframe. `null` if insufficient candle data. |
| `4h` | object \| null | Full `TrendStateApiResponse` for the 4-hour timeframe. `null` if insufficient candle data. |

Each non-null timeframe object contains the same fields as the `/trend` response (see [Section 5](#5-trend-state)).

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Always returned — individual timeframe fields may be `null` but the response itself is never 404 |

---

## 7. Dominance Matrix

```
GET /api/analysis/dominance-matrix
```

Returns a pre-computed BTC dominance capital-rotation signal for a coin. The server fetches four EMA trend states (BTC price, BTC dominance index, Coin/BTC pair, and USDT dominance), applies the full 27-scenario matrix with a USDT.D risk-on/risk-off overlay, and returns a single `directionBias` field the agent can consume without additional reasoning.

**Data sources:**
- BTC price trend — BTCUSDT candles via the external price-service API
- BTC dominance trend — BTCDOMUSDT on Binance Futures (`futuresOnly`)
- Coin/BTC pair trend — e.g. SOLBTC on Binance Spot
- USDT dominance trend — sampled from CoinGecko every minute; aggregated into 15min/1h/4h OHLC locally

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `symbol` | string | Yes | — | Coin base symbol (e.g. `SOL`, `ETH`). Not meaningful for BTC itself. |
| `timeframe` | string | No | `4h` | Candle interval used for all three EMA computations. Recommended: `4h` for macro view, `1h` for intraday. |

### Example Request

```
GET /api/analysis/dominance-matrix?symbol=SOL&timeframe=4h
```

### Example Response

```json
{
  "coin": "SOL",
  "timeframe": "4h",
  "btcTrend": "FALLING",
  "btcDominanceTrend": "BEARISH",
  "coinBtcTrend": "BULLISH",
  "usdtDominanceTrend": "BEARISH",
  "matrixSignal": "BTC falling, dominance falling, SOL/BTC rising — BTC losing more value than SOL; short BTC, not SOL | ✓ USDT.D falling (risk-on) — softening SHORT_BTC to FLAT",
  "directionBias": "FLAT",
  "btcDataAvailable": true,
  "dominanceDataAvailable": true,
  "coinBtcDataAvailable": true,
  "usdtDominanceDataAvailable": true
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `coin` | string | Coin base symbol in uppercase |
| `timeframe` | string | Candle interval used for all four EMA computations |
| `btcTrend` | string | EMA trend bias for BTC price. Values: `BULLISH` · `BEARISH` · `NEUTRAL` · `UNAVAILABLE` |
| `btcDominanceTrend` | string | EMA trend bias for BTCDOM. Values: `BULLISH` · `BEARISH` · `NEUTRAL` · `UNAVAILABLE` |
| `coinBtcTrend` | string | EMA trend bias for the Coin/BTC pair (e.g. SOLBTC). Values: `BULLISH` · `BEARISH` · `NEUTRAL` · `UNAVAILABLE` |
| `usdtDominanceTrend` | string | EMA trend bias for USDT.D (stablecoin dominance). RISING = risk-off; FALLING = risk-on. Values: `BULLISH` · `BEARISH` · `NEUTRAL` · `UNAVAILABLE` |
| `matrixSignal` | string | Human-readable explanation including any USDT.D overlay modifier |
| `directionBias` | string | Machine-readable bias after USDT.D overlay — see table below |
| `btcDataAvailable` | boolean | `false` if BTC candle data was unavailable. When `false`, `directionBias` is always `INSUFFICIENT_DATA`. |
| `dominanceDataAvailable` | boolean | `false` if BTCDOM candle data was unavailable. Matrix still runs using RANGING as fallback for dominance. |
| `coinBtcDataAvailable` | boolean | `false` if the Coin/BTC pair candle data was unavailable. Matrix still runs using RANGING as fallback. |
| `usdtDominanceDataAvailable` | boolean | `false` if USDT.D data was unavailable (CoinGecko not yet seeded). Matrix still runs with no overlay applied. |

### Direction Bias Values

| `directionBias` | Meaning |
|-----------------|---------|
| `LONG_ALT` | Capital rotating into this altcoin — best long is the coin, not BTC |
| `LONG_BTC` | Capital flowing into BTC — best long is BTC, avoid this coin |
| `LONG_BOTH` | Both BTC and this coin showing strength — both longs viable, BTC is safer |
| `SHORT_ALT` | This coin falling harder than BTC — short the coin, more profitable than shorting BTC |
| `SHORT_BTC` | BTC losing more value than this coin — short BTC, not the coin |
| `FLAT` | Conflicting or neutral signals — no clear directional edge |
| `INSUFFICIENT_DATA` | BTC trend data unavailable — matrix cannot be computed |

### Matrix Logic Summary

The server simplifies each EMA `trendBias` to `RISING` (BULLISH), `FALLING` (BEARISH), or `RANGING` (anything else). The 27-scenario core matrix is computed first, then a USDT.D risk-on/risk-off overlay is applied:

**Core 27-scenario lookup (representative rows):**

| BTC Price | BTC.D | Coin/BTC | Base Bias |
|-----------|-------|----------|-----------|
| RISING | BEARISH | RISING | `LONG_ALT` — coin outperforming in USD and vs BTC |
| RANGING | BEARISH | RISING | `LONG_ALT` — capital rotating from BTC into this coin |
| RISING | BULLISH | FALLING | `LONG_BTC` — capital flowing into BTC, avoid the altcoin |
| FALLING | BEARISH | RISING | `SHORT_BTC` — BTC losing more than the coin |
| FALLING | BEARISH | FALLING | `SHORT_ALT` — coin losing more than BTC despite broad alt resilience |
| FALLING | BULLISH | FALLING | `SHORT_ALT` — altcoins crashing harder; coin is best short |
| RISING | BULLISH | RISING | `LONG_BOTH` — rare double strength; both viable, BTC safer |
| * | * | * | See service logic for all 27 combinations |

**USDT.D overlay (applied after core matrix):**

| USDT.D Direction | Base Bias → Final Bias |
|------------------|------------------------|
| RISING (risk-off) | `LONG_ALT` → `FLAT` |
| RISING (risk-off) | `LONG_BTC` → `FLAT` |
| RISING (risk-off) | `LONG_BOTH` → `FLAT` |
| RISING (risk-off) | `FLAT` → `SHORT_ALT` |
| RISING (risk-off) | `SHORT_*` → unchanged (confirmed) |
| FALLING (risk-on) | `SHORT_ALT` → `FLAT` |
| FALLING (risk-on) | `SHORT_BTC` → `FLAT` |
| FALLING (risk-on) | `FLAT` → `LONG_ALT` |
| FALLING (risk-on) | `LONG_*` → unchanged (confirmed) |
| RANGING / unavailable | no modification |

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Always returned — never 404. Check `*DataAvailable` flags for partial results. |

---

## 8. Catalysts — Macro Events & Token Catalysts

```
GET /api/analysis/catalysts
```

Returns a unified view of upcoming macro economic events and crypto-specific token catalysts within a configurable look-ahead window. The agent can make one call and get a structured answer covering both risk domains — no need to reason about two different API formats.

**Why this endpoint exists:** The trading engine makes decisions based on technical indicators. Scheduled events can invalidate any technical setup instantly — a hawkish CPI print can dump BTC 3% in minutes, and a token unlock can override a clean chart pattern regardless of signal quality. This endpoint gives the agent awareness of those landmines before a trade is placed.

**Data sources:**
- Macro events — [Finnhub Economic Calendar](https://finnhub.io/docs/api/economic-calendar), filtered to `country=US` and `impact=high`
- Token catalysts — [CoinMarketCal v1 Events API](https://api.coinmarketcal.com), all categories (unlocks, listings, hard forks, mainnet launches, etc.)

**Caching:** Both upstream APIs are cached server-side for **60 minutes**. The server pre-fetches a 7-day window on each cache refresh. All callers with different `hours` parameters share the same warm cache — the server filters on the fly.

**Error behaviour:** If either upstream API fails or returns an unexpected schema, the affected domain returns an empty list, a human-readable entry is added to `warnings`, and a Telegram alert is sent to `DART_SIGNALS`. The response is always HTTP 200.

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `symbols` | string | No | all supported coins | Comma-separated coin base symbols to include in `tokenCatalysts` (e.g. `BTC,SOL,ETH,FIL`). When omitted, all supported coins are included. |
| `hours` | int | No | `48` | Look-ahead window size in hours. Range: 1–168 (1 hour to 7 days). Clamped automatically if out of range. |

### Example Request

```
GET /api/analysis/catalysts?symbols=BTC,ETH,SOL,FIL&hours=48
```

### Example Response

```json
{
  "generatedAt": "2026-04-17 14:30:00 UTC",
  "cacheAgeMinutes": 12,
  "windowHours": 48,
  "macroEvents": [
    {
      "name": "CPI YoY",
      "country": "US",
      "impact": "high",
      "scheduledAt": "2026-04-18 12:30:00 UTC",
      "hoursUntil": 22.0,
      "estimate": 2.9,
      "previous": 3.0
    }
  ],
  "tokenCatalysts": {
    "BTC": [],
    "ETH": [],
    "SOL": [
      {
        "type": "token_unlock",
        "description": "0.52% of circulating supply unlocks",
        "scheduledAt": "2026-04-19 00:00:00 UTC",
        "hoursUntil": 33.5
      }
    ],
    "FIL": []
  },
  "sources": {
    "macro": "finnhub",
    "token": "coinmarketcal"
  },
  "warnings": []
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `generatedAt` | string | UTC timestamp when this response was generated — `"yyyy-MM-dd HH:mm:ss UTC"` |
| `cacheAgeMinutes` | int | Minutes since the upstream API data was last refreshed. `0` = freshly fetched on this request. Maximum 59 before the cache auto-invalidates. |
| `windowHours` | int | The look-ahead window used to filter events (echoes the request parameter after clamping) |
| `macroEvents` | array | High-impact US macro events within the window, ordered soonest first. Empty when no events fall in the window or Finnhub is unreachable. |
| `tokenCatalysts` | object | Map of coin symbol → list of token catalysts. Every requested symbol appears as a key, with an empty array when no events were found. |
| `sources` | object | Provider attribution — `macro` and `token` fields identify which upstream API supplied each domain |
| `warnings` | array | Non-fatal issues: upstream API errors or unexpected schema. Empty when everything fetched cleanly. |

#### Macro Event Object

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Event name, e.g. `"CPI YoY"`, `"FOMC Statement"`, `"Nonfarm Payrolls"` |
| `country` | string | ISO country code — always `"US"` for the current filter |
| `impact` | string | Finnhub impact label — always `"high"` for the current filter |
| `scheduledAt` | string | Event time in UTC — `"yyyy-MM-dd HH:mm:ss UTC"` |
| `hoursUntil` | double | Hours from response generation time until this event, rounded to 1 decimal |
| `estimate` | double \| null | Analyst consensus estimate for the metric. `null` when not available. |
| `previous` | double \| null | Previous release value for the same metric. `null` when not available. |

#### Token Catalyst Object

| Field | Type | Description |
|-------|------|-------------|
| `type` | string | CoinMarketCal category slug — snake_case of the first category on the event. Common values: `token_unlock` · `exchange_listing` · `mainnet_launch` · `hard_fork` · `governance_vote` · `partnership` · `other` |
| `description` | string | Human-readable event description from CoinMarketCal (English) |
| `scheduledAt` | string | Event time in UTC — `"yyyy-MM-dd HH:mm:ss UTC"`. CoinMarketCal provides date only (no intraday time), so all token events are set to `00:00:00 UTC` on the event date. |
| `hoursUntil` | double | Hours from response generation time until this event, rounded to 1 decimal |

### Telegram Alerts

This endpoint sends a `DART_SIGNALS` Telegram alert under two conditions:

| Trigger | Alert message |
|---------|--------------|
| HTTP or network error calling Finnhub | `⚠️ [CatalystService] Finnhub API call failed: <error> — macro events will be empty until cache refreshes.` |
| Finnhub response missing `economicCalendar` field | `⚠️ [CatalystService] Finnhub /calendar/economic returned null or missing 'economicCalendar' field — API contract may have changed.` |
| HTTP or network error calling CoinMarketCal | `⚠️ [CatalystService] CoinMarketCal API call failed: <error> — token catalysts will be empty until cache refreshes.` |
| CoinMarketCal response missing `body` field | `⚠️ [CatalystService] CoinMarketCal /events returned null or missing 'body' field — API contract may have changed.` |
| Any unexpected parsing exception | `⚠️ [CatalystService] Unexpected error parsing <provider> response: <error> — possible API contract change.` |

Alerts fire at most once per cache refresh cycle (every 60 minutes), so they do not spam the channel on repeated calls.

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Always returned — never 404. Check `warnings` for partial results. |

---

## Supported Coins

### Order Book (`/orderbook`)

Support depends on the chosen exchange. The wall-analysis algorithm requires a configured bin size per coin.

| Symbol | Binance | Bitunix | Hyperliquid | dYdX |
|--------|---------|---------|-------------|------|
| BTC | ✓ | ✓ | ✓ | ✓ |
| ETH | ✓ | ✓ | ✓ | ✓ |
| BNB | ✓ | ✓ | ✓ | ✓ |
| SOL | ✓ | ✓ | ✓ | ✓ |
| XRP | ✓ | ✓ | ✓ | ✓ |
| DOGE | ✓ | ✓ | ✓ | ✓ |
| ADA | ✓ | ✓ | ✓ | ✓ |
| TRX | ✓ | ✓ | — | — |
| MATIC | ✓ | ✓ | — | — |
| POL | ✓ | ✓ | — | — |
| DOT | ✓ | ✓ | ✓ | — |
| BCH | ✓ | ✓ | ✓ | ✓ |
| SUI | ✓ | ✓ | ✓ | ✓ |
| HBAR | ✓ | ✓ | — | — |
| VIRTUAL | ✓ | ✓ | — | — |
| NIGHT | ✓ | ✓ | — | — |
| CHZ | ✓ | ✓ | — | — |
| CAKE | ✓ | ✓ | — | — |
| ZEC | ✓ | ✓ | — | — |
| WLD | ✓ | ✓ | ✓ | — |
| ASTER | ✓ | ✓ | — | — |
| LDO | ✓ | ✓ | ✓ | — |
| HYPE | ✓ | ✓ | ✓ | — |
| ARB | ✓ | ✓ | ✓ | — |
| FET | ✓ | ✓ | ✓ | — |
| FIL | ✓ | ✓ | ✓ | — |

> If a coin is not listed by the chosen exchange, the endpoint returns **HTTP 404**.

### Indicators (`/indicators`)

All coins listed above are supported. Data source is always Binance Futures.

### Backtest (`/backtest` and `/backtest/top`)

The backtest uses candle data stored in the local PostgreSQL database. Supported coins:

```
BTC, ETH, BNB, SOL, XRP, DOGE, ADA, TRX, MATIC, POL, DOT, BCH,
SUI, HBAR, VIRTUAL, NIGHT, CHZ, CAKE, ZEC, WLD, ASTER, LDO,
HYPE, ARB, FET, FIL
```

> The `/backtest/top` endpoint always iterates over the full list above. Coins with
> insufficient candle history (< 302 candles for the requested timeframe) are silently
> skipped.

### Trend (`/trend` and `/trend/multi`)

Candles are fetched live from the external price-service API (up to 1500). All supported coins are available on all supported timeframes, subject to sufficient candle history being available (minimum: EMA99 period + lookback + 1 candles):

```
BTC, ETH, BNB, SOL, XRP, DOGE, ADA, TRX, MATIC, POL, DOT, BCH,
SUI, HBAR, VIRTUAL, NIGHT, CHZ, CAKE, ZEC, WLD, ASTER, LDO,
HYPE, ARB, FET, FIL
```

### Dominance Matrix (`/dominance-matrix`)

The dominance matrix requires three internal symbol lookups. The `symbol` parameter is the altcoin to analyse:

- **BTC price** — always fetched as `BTCUSDT`
- **BTC Dominance** — fetched as `BTCDOMUSDT` (Binance Futures). History may be limited for newer candle windows.
- **Coin/BTC pair** — the following coins have a registered BTC spot pair in the price service:

```
ETH  (ETHBTC)   BNB  (BNBBTC)   SOL  (SOLBTC)   XRP  (XRPBTC)
ADA  (ADABTC)   DOGE (DOGEBTC)  DOT  (DOTBTC)   BCH  (BCHBTC)
TRX  (TRXBTC)   LDO  (LDOBTC)   ARB  (ARBBTC)   FIL  (FILBTC)
MATIC(MATICBTC) POL  (POLBTC)   SUI  (SUIBTC)   HBAR (HBARBTC)
CHZ  (CHZBTC)   CAKE (CAKEBTC)  ZEC  (ZECBTC)   WLD  (WLDBTC)
FET  (FETBTC)
```

Coins **not** in the list above will return `coinBtcDataAvailable: false`. The matrix still runs but uses `RANGING` as the Coin/BTC fallback — treat the result as lower confidence for those coins.

The following 4 coins have **no BTC pair on Binance** (Spot or Futures) and will always return `coinBtcDataAvailable: false`:

```
VIRTUAL, NIGHT, ASTER, HYPE
```

> **Note:** Do not pass `BTC` as the `symbol` parameter — BTCBTC is not a valid pair. Use the dominance matrix only for altcoins.

---

## Understanding Backtest Results

### What "unresolved" means

After a signal is found at candle `i`, the engine scans all remaining candles for a TP or SL hit. If neither is reached before the end of the dataset, the trade is marked **unresolved** — it was neither a win nor a loss within the observation window.

`unresolved` trades are excluded from `winRate` calculations.

### What `bestRR` means

For each R/R ratio, a combined score is computed:

```
overallWinRate = totalWins / (totalWins + totalLosses) × 100
score = overallWinRate × ratio
```

The ratio with the highest score is returned as `bestRR`. A higher ratio amplifies the win rate, so 1:5 at 60% (score = 300) beats 1:3 at 70% (score = 210).

### Limitations

- Backtest does **not** simulate position sizing, slippage, or fees
- Signals that fire on consecutive candles can share future candles — this is expected behaviour matching the live engine
- CVD-based conditions (validation conditions 15/16) are skipped in the backtest to keep it deterministic

---

## Quick-Start Examples

Production base: `http://193.36.85.229:8080`

### Check BTC order book walls on Binance

```bash
curl "http://193.36.85.229:8080/api/analysis/orderbook?symbol=BTC&exchange=binance"
```

### Check ETH with a custom reference price

```bash
curl "http://193.36.85.229:8080/api/analysis/orderbook?symbol=ETH&exchange=bitunix&refPrice=3200"
```

### Get market indicators for SOL (includes funding rate)

```bash
curl "http://193.36.85.229:8080/api/analysis/indicators?symbol=SOL"
```

### Run a 15-min backtest on BNB (last 500 candles)

```bash
curl "http://193.36.85.229:8080/api/analysis/backtest?symbol=BNB&timeframe=15min&candleLimit=500"
```

### Get the top-10 most profitable setups across all coins (1h candles)

```bash
curl "http://193.36.85.229:8080/api/analysis/backtest/top?timeframe=1h&candleLimit=1500"
```

### Check the 1h trend state for LDO

```bash
curl "http://193.36.85.229:8080/api/analysis/trend?symbol=LDO&timeframe=1h"
```

### Check the 4h trend state for HYPE with a 20-candle lookback

```bash
curl "http://193.36.85.229:8080/api/analysis/trend?symbol=HYPE&timeframe=4h&lookback=20"
```

### Get all three timeframes (15min + 1h + 4h) for SOL in one call

```bash
curl "http://193.36.85.229:8080/api/analysis/trend/multi?symbol=SOL"
```

### Check the dominance matrix for SOL on the 4h timeframe

```bash
curl "http://193.36.85.229:8080/api/analysis/dominance-matrix?symbol=SOL&timeframe=4h"
```

### Check the dominance matrix for ETH on the 1h timeframe (intraday view)

```bash
curl "http://193.36.85.229:8080/api/analysis/dominance-matrix?symbol=ETH&timeframe=1h"
```

### Check catalysts for BTC, SOL, ETH, FIL in the next 48 hours

```bash
curl "http://193.36.85.229:8080/api/analysis/catalysts?symbols=BTC,SOL,ETH,FIL&hours=48"
```

### Check catalysts for all supported coins in the next 24 hours

```bash
curl "http://193.36.85.229:8080/api/analysis/catalysts?hours=24"
```

### Check the full 7-day catalyst window for SOL and ETH

```bash
curl "http://193.36.85.229:8080/api/analysis/catalysts?symbols=SOL,ETH&hours=168"
```

### List all open journal trades with unrealized PnL

```bash
curl "http://193.36.85.229:8080/api/analysis/journal?status=OPEN"
```

### List the 20 most recent closed journal trades (WIN + LOSS combined)

```bash
curl "http://193.36.85.229:8080/api/analysis/journal?status=ALL&limit=20"
```

### List the last 10 engine-generated WIN positions for BTC

```bash
curl "http://193.36.85.229:8080/api/analysis/positions?status=WIN&coin=BTC&limit=10"
```

### Show all currently open exchange positions

```bash
curl "http://193.36.85.229:8080/api/analysis/positions?status=OPEN"
```

---

## 9. Trade Journal

```
GET /api/analysis/journal
```

Returns aggregate statistics across the full personal trade journal plus a filtered, paginated list of entries.
Entries are logged manually via the `/journal` Telegram command and auto-resolved (WIN / LOSS) when TP or SL is hit based on live Bitunix price.

> OPEN entries include a real-time `unrealizedPnl` field computed against the current Bitunix live price.
> This field is `null` for closed entries or when the live price fetch fails.

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | string | No | `ALL` | Filter entries by lifecycle status. One of: `ALL` · `OPEN` · `WIN` · `LOSS` |
| `limit` | int | No | `50` | Maximum number of entries to return (1–500) |

### Example Request

```
GET /api/analysis/journal?status=OPEN
```

### Example Response

```json
{
  "requestedStatus": "OPEN",
  "totalOpen": 2,
  "totalWin": 14,
  "totalLoss": 6,
  "winRate": 70.0,
  "totalRealisedPnl": 312.45,
  "entries": [
    {
      "id": 42,
      "symbol": "BTC",
      "direction": "LONG",
      "entryPrice": 83500.0,
      "sl": 81000.0,
      "tp": 91000.0,
      "rrRatio": 3,
      "leverage": 30,
      "riskAmountUsdt": 50.0,
      "positionNotional": 1670.0,
      "engagedMargin": 55.67,
      "feeTier": "VIP0",
      "openFee": 1.34,
      "closeFee": null,
      "status": "OPEN",
      "openedAt": "2026-04-15 09:30",
      "closedAt": null,
      "exitPrice": null,
      "pnl": null,
      "unrealizedPnl": 42.18
    }
  ]
}
```

### Response Fields — Top Level

| Field | Type | Description |
|-------|------|-------------|
| `requestedStatus` | string | The status filter that was applied to `entries` |
| `totalOpen` | int | Total OPEN entries across the full journal (unfiltered) |
| `totalWin` | int | Total WIN entries across the full journal (unfiltered) |
| `totalLoss` | int | Total LOSS entries across the full journal (unfiltered) |
| `winRate` | double | Win rate as a percentage of resolved (WIN+LOSS) trades |
| `totalRealisedPnl` | double | Sum of net P&L in USDT across all closed trades (full journal) |
| `entries` | array | Filtered, capped list of journal entries (see below) |

### Response Fields — JournalEntry

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | long | No | Database primary key |
| `symbol` | string | No | Coin base symbol (e.g. `"BTC"`) |
| `direction` | string | No | `"LONG"` or `"SHORT"` |
| `entryPrice` | double | No | Entry price in USDT |
| `sl` | double | No | Stop-loss price |
| `tp` | double | No | Take-profit price |
| `rrRatio` | int | No | R/R ratio used (e.g. `3` = 1:3) |
| `leverage` | int | No | Leverage at open |
| `riskAmountUsdt` | double | No | Dollar risk on this trade |
| `positionNotional` | double | No | Full position value in USDT |
| `engagedMargin` | double | No | Margin locked = notional / leverage |
| `feeTier` | string | No | Bitunix fee tier (e.g. `"VIP0"`) |
| `openFee` | double | Yes | Taker fee paid at open in USDT |
| `closeFee` | double | Yes | Taker fee paid at close. `null` while OPEN |
| `status` | string | No | `"OPEN"` · `"WIN"` · `"LOSS"` |
| `openedAt` | string | No | Open timestamp `"yyyy-MM-dd HH:mm"` |
| `closedAt` | string | Yes | Close timestamp. `null` while OPEN |
| `exitPrice` | double | Yes | Exit price. `null` while OPEN |
| `pnl` | double | Yes | Realised net P&L in USDT. `null` while OPEN |
| `unrealizedPnl` | double | Yes | Live unrealized gross P&L. Populated for OPEN only; `null` otherwise or on price-fetch failure |

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success — always returned |

---

## 10. Exchange Positions

```
GET /api/analysis/positions
```

Returns aggregate counters and a filtered list of engine-generated exchange positions — the AI signal results placed (or validated but not placed) on Bitunix by the trading engine.

Lifecycle:
- `OPEN` — position is live on the exchange
- `WIN` — closed at take-profit
- `LOSS` — closed at stop-loss
- `NOTOPEN` — signal was validated but no order was placed (forward-test mode)
- `TIMEOUT` — candle window expired before TP/SL was hit

> Note: `totalNetPnl` in the response covers only WIN and LOSS positions (real closed trades). NOTOPEN and TIMEOUT records are excluded from the P&L sum.

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `status` | string | No | `ALL` | Filter positions. One of: `ALL` · `OPEN` · `WIN` · `LOSS` |
| `coin` | string | No | — | Optional coin base symbol filter (e.g. `"BTC"`). Omit for all coins. |
| `limit` | int | No | `50` | Maximum number of positions to return (1–500) |

> `ALL` returns the most recent open positions merged with the most recent WIN/LOSS closed positions, sorted by `openTime` descending.

### Example Request

```
GET /api/analysis/positions?status=WIN&coin=BTC&limit=10
```

### Example Response

```json
{
  "requestedStatus": "WIN",
  "totalOpen": 1,
  "totalWin": 87,
  "totalLoss": 43,
  "totalNotOpen": 12,
  "totalTimeout": 5,
  "totalNetPnl": 1845.60,
  "positions": [
    {
      "id": 310,
      "coin": "BTC",
      "signal": "LONG",
      "entryPrice": 82000.0,
      "stopLossPrice": 79500.0,
      "targetPrice": 89500.0,
      "stopLossPercent": 3.05,
      "positionSizeUsdt": 1640.0,
      "closed": true,
      "result": "WIN",
      "openTime": "2026-04-12 14:01",
      "closeTime": "2026-04-13 06:45",
      "rawProfit": 149.82,
      "netProfit": 144.10,
      "profitPercent": 8.79,
      "validationProfile": "current-v1-long"
    }
  ]
}
```

### Response Fields — Top Level

| Field | Type | Description |
|-------|------|-------------|
| `requestedStatus` | string | Status filter applied to `positions` |
| `totalOpen` | int | Total currently OPEN positions (full history, unfiltered) |
| `totalWin` | int | Total WIN positions (full history, unfiltered) |
| `totalLoss` | int | Total LOSS positions (full history, unfiltered) |
| `totalNotOpen` | int | Total NOTOPEN records (forward-test, no real order placed) |
| `totalTimeout` | int | Total TIMEOUT records (window expired before TP/SL) |
| `totalNetPnl` | double | Sum of net P&L in USDT across all WIN + LOSS positions (full history) |
| `positions` | array | Filtered, capped list of positions (see below) |

### Response Fields — ExchangePosition

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
| `id` | long | No | Database primary key |
| `coin` | string | No | Coin base symbol (e.g. `"BTC"`) |
| `signal` | string | No | Direction: `"LONG"` or `"SHORT"` |
| `entryPrice` | double | Yes | Entry price in USDT at order placement |
| `stopLossPrice` | double | Yes | Stop-loss price |
| `targetPrice` | double | Yes | Take-profit price |
| `stopLossPercent` | double | Yes | SL distance as % of entry price |
| `positionSizeUsdt` | double | Yes | Total position notional in USDT |
| `closed` | boolean | No | `true` once the position is closed |
| `result` | string | Yes | `"OPEN"` · `"WIN"` · `"LOSS"` · `"NOTOPEN"` · `"TIMEOUT"`. `null` while open |
| `openTime` | string | Yes | Open timestamp `"yyyy-MM-dd HH:mm"` |
| `closeTime` | string | Yes | Close timestamp. `null` while OPEN |
| `rawProfit` | double | Yes | Gross P&L before fees in USDT. `null` while OPEN |
| `netProfit` | double | Yes | Net P&L after fees in USDT. `null` while OPEN |
| `profitPercent` | double | Yes | Net P&L as % of position size. `null` while OPEN |
| `validationProfile` | string | Yes | Validation profile name that approved the signal (e.g. `"current-v1-long"`). `null` for older records |

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success — always returned |

---

## 8. Historical Candles (Price Service)

```
GET /klines/online-candles
```

> **This endpoint lives on the Price Service** (`http://193.36.85.229:8081`), not the Analysis API (`8080`). It is the canonical source for historical OHLC candle data — used by the report review agent to check trade outcomes.

Returns up to 1500 historical candles for a coin at a given timeframe, fetched live from Binance via the internal price service.

### Query Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `symbol` | string | Yes | — | Coin base symbol (e.g., `BTC`, `ETH`, `FIL`) or full pair (e.g., `BTCUSDT`). Supports the same coin list as the Analysis API, plus BTC pairs (e.g., `SOLBTC`, `ETHBTC`). |
| `granularity` | string | Yes | — | Candle interval: `1m` · `5m` · `15m` · `1h` · `4h` · `1d` |
| `limit` | int | Yes | — | Number of candles to return. Range: 1–1500 (Binance API max). |

### Example Request

```bash
curl "http://193.36.85.229:8081/klines/online-candles?symbol=FIL&granularity=15m&limit=1500"
```

### Example Response

```json
[
  {
    "id": 7521912,
    "symbol": "FIL",
    "granularity": "15m",
    "timestamp": 1732464000000,
    "closeTimeStamp": 1732464899999,
    "openPrice": 0.9823,
    "highestPrice": 0.9845,
    "lowestPrice": 0.9789,
    "closePrice": 0.9812,
    "baseCurrencyTradingVolume": 12345.67,
    "quoteCurrencyTradingVolume": 12123.45,
    "usdtVol": 12123.45,
    "numberOfTrades": "456",
    "takerBuyBaseVolume": "6789.01",
    "takerBuyQuoteVolume": "6661.23",
    "updatedAt": 1732464123456
  }
]
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | long | Unique candle identifier |
| `symbol` | string | Coin base symbol in uppercase |
| `granularity` | string | Candle interval (echoes request) |
| `timestamp` | long | Candle open time in milliseconds since epoch (UTC) |
| `closeTimeStamp` | long | Candle close time in milliseconds since epoch (UTC) |
| `openPrice` | double | Opening price in USDT |
| `highestPrice` | double | Highest price during the candle period |
| `lowestPrice` | double | Lowest price during the candle period |
| `closePrice` | double | Closing price in USDT |
| `baseCurrencyTradingVolume` | double | Volume in base currency (e.g., FIL) |
| `quoteCurrencyTradingVolume` | double | Volume in quote currency (USDT) |
| `usdtVol` | double | Volume in USDT |
| `numberOfTrades` | string | Number of trades in the candle period |
| `takerBuyBaseVolume` | string | Taker buy volume in base currency |
| `takerBuyQuoteVolume` | string | Taker buy volume in quote currency |
| `updatedAt` | long | Last update timestamp in milliseconds since epoch |

### Coverage

| Granularity | 1500 candles covers |
|---|---|
| `1m` | ~25 hours |
| `5m` | ~5.2 days |
| `15m` | ~15.6 days |
| `1h` | ~62.5 days |
| `4h` | ~250 days |
| `1d` | ~4.1 years |

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success — returns a JSON array (may be empty if the coin has no data) |
| 500 | Internal error (e.g., Binance API unreachable) |
