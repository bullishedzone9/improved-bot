# ARC_SILK — RoboForex MT4 demo validation

## Scope and exclusions

This workstream targets **RoboForex MT4 demo only**. Exness is paused. Do not merge this branch into `main`, deploy a funded account, or enable live trading as part of this validation.

The repository contains two separate EAs:

- `ARC_SILK_AutoTrader.mq4` v0.2.0: the trading prototype. It can submit demo orders only when explicitly enabled; it refuses non-demo accounts and defaults to `EnableDemoTrading=false`.
- `ARC_SILK_MT4_Bridge.mq4` v0.2.1: a separate read-only quote telemetry exporter. It never submits, modifies, or closes orders. HTTP telemetry defaults to disabled.

The read-only bridge is not the trading bot. The trading EA is not the telemetry bridge.

## Current verification baseline

- GitHub Actions run 83 on `feature/mt4-bridge-foundation`: passed Python compilation, unit tests, static EA safety checks, and Streamlit startup smoke test.
- The EA safety script is a source-level check only. It is **not** an MQL4/MetaEditor compilation.
- MetaEditor compilation: not verified.
- RoboForex Strategy Tester: not verified.
- RoboForex demo forward execution: not verified.
- Live trading: prohibited for this workstream.

## RoboForex-specific checks

Before enabling any demo orders, record these values from the RoboForex MT4 terminal and the selected demo account. Do not put account passwords, investor passwords, API keys, or tokens in GitHub or chat.

1. Exact demo server name shown in MT4.
2. Account type (for example, Pro, ECN, Prime, or ProCent).
3. Exact chart symbol, including any broker suffix.
4. Symbol digits, point size, tick size, and tick value.
5. Minimum lot, maximum lot, and lot step.
6. Stop level and freeze level.
7. Observed spread during the intended test session.
8. Whether the broker/account execution mode accepts stop-loss and take-profit values on the initial market order.

The EA uses the chart's `Symbol()` and broker-reported symbol properties rather than hardcoding a currency-pair name. This still requires verification against the actual RoboForex demo contract specifications.

## Required test sequence

### Gate 1 — Compile

- Copy `mt4/ARC_SILK_AutoTrader.mq4` into the RoboForex MT4 `MQL4/Experts` directory.
- Compile it in the MetaEditor bundled with that MT4 installation.
- Record the exact compiler result and warnings.
- Keep `EnableDemoTrading=false`.

### Gate 2 — Strategy Tester

- Use RoboForex historical data for the exact symbol and timeframe.
- Model spread, commission, swap, and slippage conservatively.
- Use chronological in-sample and held-out out-of-sample periods.
- Report profit factor, maximum equity drawdown, trade count, expectancy, and net return after costs.
- Reject parameter sets that only work on the in-sample period.
- Do not infer profitability from the source-level CI checks.

### Gate 3 — Demo-terminal compatibility

Only after Gates 1 and 2 pass:

- Attach the EA to a RoboForex demo chart with trading still disabled.
- Confirm initialization, symbol properties, spread readings, and Experts/Journal logs.
- Confirm the EA rejects a non-demo account in a controlled, non-trading check if one is available.
- Verify calculated lot size is never rounded upward to the broker minimum when that would exceed configured risk.
- Verify stop distances and margin checks against the account's contract settings.

### Gate 4 — Limited demo forward test

Only after explicit approval to enable demo orders:

- Confirm the terminal is connected to the intended RoboForex demo server.
- Set `EnableDemoTrading=true` locally in the EA inputs; do not commit a changed default.
- Keep per-trade risk at or below the source default of 0.5% and daily equity-loss lock at or below 2%.
- Monitor every order, rejection, spread, stop distance, lot size, and daily loss.
- Stop the test on unexplained sizing, execution, or risk-control discrepancies.

## Known EA limitations requiring review

- The current daily-loss control blocks new entries after the threshold; it does not automatically close existing positions.
- The open-position cap is scoped to the current symbol and magic number, not a global cap across every symbol.
- Broker execution rules can differ by account type. An initial `OrderSend` with attached SL/TP may be rejected by some execution configurations; do not work around this by adding order modification until that behavior is verified and reviewed.
- Spread and stop-level thresholds must be calibrated from the selected RoboForex demo account, not guessed.
- Strategy validation previously showed weak results (profit factor below 1, drawdown above the project target, and negative out-of-sample return). This strategy is not approved for funded trading.

## No-desktop constraint

Development, documentation, source review, and Python CI can continue from a phone. MQL4 compilation and MT4 Strategy Tester/forward testing require a Windows MT4 terminal. A browser-only MT4/WebTrader session or Android MT4 app does not compile or host this EA. Do not claim deployment or terminal testing until a Windows terminal is actually available.

## Credential handling

Never request or commit the RoboForex trading password, investor password, account number, or any one-time code. For support and diagnostics, use only non-sensitive details such as account type, server label, symbol properties, compiler output, and redacted logs.
