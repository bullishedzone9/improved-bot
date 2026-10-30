# Phase 5 — Historical OHLC data intake

The project now includes a strict CSV intake path and a command-line runner for the fixed-parameter chronological holdout evaluator.

## Accepted input
CSV columns required: `date,open,high,low,close`. An optional volume column is ignored. Rows must have unique, valid, increasing timestamps; OHLC prices must be numeric, finite, positive and internally consistent. The loader normalizes timestamps to UTC and rejects malformed rows rather than filling or inventing data.

## Run from a Python environment
```bash
python run_research.py path/to/your_historical_export.csv --fast 20 --slow 50 --train-fraction 0.70 --cost-bps 2
```
The cost value is a per-side estimate in basis points and must be calibrated to actual spread, commission and slippage. It is not a RoboForex quote.

## Data needed for meaningful results
Export genuine historical bars from the relevant RoboForex MT4 demo symbol and timeframe (for example EURUSD M15), preserving timestamps and OHLC. Do not use `sample_data/demo_forex_sample.csv` as market evidence: it is synthetic software-test data. Keep the symbol, timeframe, broker server, export date range and timezone documented with the file.

## Limits
This run is a long-or-cash SMA close-price evaluation. It is not the EA's ATR stop/target strategy and does not model broker fills, swaps, gaps, variable spread, lot sizing or intrabar execution. It cannot establish profitability or authorize live trading.
