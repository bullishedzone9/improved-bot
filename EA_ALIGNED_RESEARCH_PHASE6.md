# Phase 6 — EA-aligned strategy research prototype

This module is a research approximation of the MT4 EA's EMA(20/50) closed-bar crossover and ATR(14) stop/target logic. It is separate from the SMA holdout evaluator; never mix their results.

## Run
```bash
python run_ea_research.py path/to/export.csv --spread-points 12 --point 0.0001
```
CSV must contain date,open,high,low,close. Data is assumed BID-side. Configure spread and point for the exact symbol and broker quote format.

## Assumptions and limits
- Signals are calculated on completed bars; entries are next-bar open.
- ATR uses Wilder-style smoothing as an approximation to MT4 iATR.
- BUY entry uses ask (bid open + spread); long exits use bid. Short exits use ask.
- If SL and TP both fall inside one OHLC candle, stop is assumed first.
- Risk is modeled as a fixed fraction of equity per stop distance; actual MT4 lot sizing, tick value, min lot, margin and contract specification are not simulated.
- Commission, swap, variable spread, slippage, gaps, execution latency, stop-level restrictions and broker fills are not modeled.
- The EA's daily equity lock prevents new entries but does not close existing positions; the simulator preserves that behavior.
- This is not an exact MetaTrader 4 Strategy Tester replica. Compare trade-by-trade with MT4 demo Strategy Tester before interpreting results.

This prototype is research-only. Do not use results to authorize live trading.
