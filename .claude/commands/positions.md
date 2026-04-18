Fetch all open journal positions and recommend an action for each one, following the Phase 7 rules defined in @crypto-agent-trading-prompt.md. Execute immediately without asking questions.

## Steps

### Step 1 — Fetch open positions

```
GET http://193.36.85.229:8080/api/analysis/journal?status=OPEN
```

Use `curl -s` via Bash (HTTP only — never WebFetch). If `totalOpen == 0`, print "No open positions in journal." and stop.

### Step 2 — Fetch current market data for each position

For each open position, run these three calls in parallel (group all positions into one parallel Bash block if possible):

```
GET http://193.36.85.229:8080/api/analysis/trend/multi?symbol={SYMBOL}&lookback=10
GET http://193.36.85.229:8080/api/analysis/orderbook?symbol={SYMBOL}&exchange=bitunix
GET http://193.36.85.229:8080/api/analysis/indicators?symbol={SYMBOL}
```

If two open positions share the same symbol, fetch only once and reuse.

### Step 3 — For each position, compute and output

**Calculate:**
- Progress to TP: `(currentPrice − entryPrice) / (tp − entryPrice) × 100` for LONG; reverse for SHORT
- Progress to SL: `(entryPrice − currentPrice) / (entryPrice − sl) × 100` for LONG; reverse for SHORT
- Distance to TP and SL as % of current price
- Hold duration in hours since `openedAt`

**Pick one primary action** from the fixed set — no other action types allowed:

| Action | When |
|---|---|
| HOLD | Progress to TP 0–40%, trend still aligned, no new wall blocking path |
| MOVE_SL_TO_BREAKEVEN | Progress to TP ≥ 50% AND trend still aligned |
| PARTIAL_CLOSE | Progress to TP ≥ 50% — recommend closing 30–50%, leave rest running |
| TIGHTEN_TP | New strong wall (l+) formed between current price and original TP — provide the new TP number |
| CLOSE_NOW | Thesis broken: higher-TF trend flipped against position, OR 3+ indicators flipped, OR high-impact macro within 24h on wrong side |
| WATCH | Mixed signals, no clean action — flag for next run |

You may also recommend one or more follow-up actions from the same fixed set (e.g., MOVE_SL_TO_BREAKEVEN + PARTIAL_CLOSE).

**Output format for each position:**

```
═══════════════════════════════════════
OPEN POSITION: {SYMBOL} {DIRECTION}
═══════════════════════════════════════

ENTRY SNAPSHOT
  Entry Price:    ${entryPrice}   Opened: {openedAt} UTC ({X}h ago)
  Stop-Loss:      ${sl}           Take-Profit: ${tp}
  RR Ratio:       1:{rrRatio}
  Unrealized PnL: ${unrealizedPnl}

CURRENT MARKET
  Live Price:     ${currentPrice}
  Progress:       {X}% to TP | {Y}% to SL
  Trend (1h):     {trendBias}  | Trend (4h): {trendBias}
  Indicators aligned with position: {n}/4
  New wall(s) formed: {yes — describe / no}

RECOMMENDATION
  Primary Action:    {ACTION_NAME}
  Follow-up Actions: {ACTION_NAME_1, ACTION_NAME_2 or "none"}
  Rationale:         {2-3 sentences referencing specific data — wall prices, trend states, indicator signals}

  {If TIGHTEN_TP: New TP: ${newTp} — {distance}% from live price}
  {If MOVE_SL_TO_BREAKEVEN: New SL: ${entryPrice} (breakeven)}
  {If PARTIAL_CLOSE: Close {30-50}% of position, keep remainder with current/moved SL and TP}

NOTE: No new setup scan was run. Use /dart or /btc for full cross-reference analysis.

═══════════════════════════════════════
```

Print a brief summary at the end:

```
─────────────────────────────
POSITIONS SUMMARY ({n} open)
  {SYMBOL} {DIR}: {PRIMARY_ACTION}
  {SYMBOL} {DIR}: {PRIMARY_ACTION}
  ...
─────────────────────────────
```

### Behaviour rules

- Start immediately. Do not ask questions.
- Use `curl -s "http://..."` via Bash for all API calls. Never use WebFetch.
- If an API call fails for a coin, note the failure in that position's block and output "WATCH — data unavailable" as the action.
- Wall strength filter: only walls tagged `l` or stronger are considered for TIGHTEN_TP decisions. Weaker walls (xs, s, m) are noise.
- Do not save any report file — this command is read-only, output to terminal only.
