# Live Trading Readiness — SILKOUS Forex Intelligence

## Current verified status

- Repository: `bullishedzone9/improved-bot`
- Added `mt4/ARC_SILK_AutoTrader.mq4` on branch `codex/live-trading-readiness`.
- The EA source has been statically reviewed and corrected into a complete, demo-only MQL4 source file.
- **Not compiled:** no MetaEditor/MQL4 compiler is available in this environment. No successful compile is claimed.
- No live-execution bridge has been built or connected. Keep bridge work paused until MetaEditor compilation and Strategy Tester checks pass.
- The Streamlit research dashboard remains separate from MT4 and has no broker execution connection.
- The existing GitHub Actions Python tests do not compile or validate MQL4.

## EA safety defaults and scope

- `EnableDemoTrading = false`; no order is sent until deliberately enabled on a broker demo account.
- `IsDemo()` is checked during initialization and before order submission. Non-demo accounts are rejected.
- Closed-candle EMA crossover; ATR-based stop; risk-based lot sizing rounds down and refuses sizes below broker minimum.
- Maximum spread, broker stop/freeze distance, free-margin check, position count, and account/day global-variable loss baseline are checked.
- Daily-loss baseline is first initialized when this EA runs on that server day. For accurate day-start loss measurement, initialize/verify it against actual day-start equity before demo testing; a terminal that starts late cannot infer the missing equity history.
- The EA's daily-loss guard blocks new entries; it does not forcibly close existing positions.
- This is a single EA instance design with a configurable open-position count for the magic number. Multi-chart/multi-symbol exposure must be separately reviewed before use.
- No network calls, DLL imports, credentials, or bridge endpoints are included.

## Required local compile and test gate

1. On a Windows computer with MetaTrader 4 installed, open MetaEditor from MT4.
2. Open `mt4/ARC_SILK_AutoTrader.mq4` from this repository and press Compile.
3. Record the MetaEditor build/version and confirm **0 errors**. Resolve any compiler warnings before proceeding.
4. In Strategy Tester, use historical data and realistic spread/commission/swap assumptions. Inspect trade count, max drawdown, risk per trade, stop/target placement, and behavior during gaps/high spread. This is a software/strategy test, not evidence of future profitability.
5. Run first with `EnableDemoTrading=false`; confirm no orders are submitted.
6. Only after a clean compile and source review, set `EnableDemoTrading=true` on a dedicated demo account and forward-test. Confirm every order's lot size, SL/TP, journal log, and daily-loss behavior.
7. Do not enable or connect live execution as part of this stage.

## Staged release gate

### Stage 1 — Complete EA verification
- Compile in MetaEditor and fix all compiler errors/warnings.
- Verify broker-specific tick value/size, volume step/min/max, stop levels, symbols, and margin checks.
- Verify account-wide daily-loss baseline semantics, multiple-chart behavior, reconnect behavior, and duplicate-order handling.
- Backtest and demo forward-test; preserve logs and settings.

### Stage 2 — Build a secure demo-only bridge (only after Stage 1 passes)
- HTTPS endpoint, server-side secret store, per-request authentication, timestamp/expiry, nonce, and idempotency key.
- Reject replayed, stale, malformed, duplicate, or unauthorized commands.
- Start with read-only health/quote/status messages. Do not expose an unauthenticated endpoint that can issue orders.
- Use broker-terminal quotes for execution checks, not the dashboard's third-party snapshot.
- Hard caps on risk, lots, open positions, spread, allowed symbols, trading sessions, and daily loss; mandatory SL; audit log; emergency kill switch.

### Stage 3 — End-to-end demo verification
- Verify EA → bridge → validation/risk checks → MT4 demo terminal → broker acknowledgement → audit record.
- Test rejects for expired requests, bad authentication, duplicate requests, invalid symbol/volume, missing stop-loss, excessive spread, daily-loss cap, and network interruption.
- Run a sustained demo soak test and reconcile requested, accepted, rejected, and filled orders.

### Stage 4 — Live-mode release gate
Live execution remains disabled until earlier stages pass and the user explicitly approves a separate final release after reviewing the test evidence and risks. A successful build, deployment, or demo trade alone is not sufficient.

## Current next action

Compile `mt4/ARC_SILK_AutoTrader.mq4` in MetaEditor and provide the exact compiler output. The source has not been compiled in this environment; do not treat it as verified executable software.
