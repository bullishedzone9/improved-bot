# ARC_SILK On-Demand Agent — Phase 3 paper simulator

## Scope

Adds deterministic, offline paper-trade simulation. It does not connect to RoboForex, request credentials, submit broker orders, or run a background process.

## Simulation rules

- Entry is the first future candle's open after the signal.
- Stop and target levels are fixed from the candidate signal.
- If both stop and target are touched in one candle, stop is assumed first (conservative; OHLC data cannot reveal intrabar ordering).
- If price gaps through the stop at candle open, the open is used as the adverse exit.
- If neither level is reached, the final available close is used (end-of-data mark-to-market).
- Risk amount is starting equity multiplied by risk percent; risk percent is hard-capped at 0.25%.
- Caller supplies aggregate transaction costs as `costs_r` (spread, commission and slippage expressed in units of initial risk). The simulator subtracts these costs from gross R.
- Rejects trades when the supplied daily loss is at or above the configured lock.
- Results are explicitly marked `PAPER_ONLY_NO_BROKER_ORDER`.

## Run

```bash
python -m unittest tests.test_paper_simulation -v
```

## Limitations

This is a unit-testable trade outcome simulator, not a full portfolio backtester. It assumes one trade at a time and does not model broker lot sizing, contract specifications, swaps, variable commissions, partial fills, liquidity, market impact, or intrabar tick sequence. The caller must supply realistic cost estimates. It must not be presented as evidence of strategy profitability.

## Next gates

1. Add historical walk-forward portfolio simulation with instrument-specific contract and cost data.
2. Validate strategy performance out of sample before any demo forward execution.
3. Verify a broker-authorized demo execution API independently.
4. Keep all broker execution disabled until explicit demo-only authorization and end-to-end tests.
