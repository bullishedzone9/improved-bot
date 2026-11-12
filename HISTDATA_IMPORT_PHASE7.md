# Phase 7 — HistData M1 import and M15 preparation

The project now supports HistData Generic ASCII M1 bars and can aggregate them into complete M15 bars for research.

## Source format and timezone
HistData documents Generic ASCII M1 as six semicolon-separated fields without a header: timestamp, open, high, low, close, volume. Its timestamps use fixed Eastern Standard Time (UTC-5) with no daylight-saving adjustment. The importer therefore adds exactly five hours and records UTC timestamps. See the provider FAQ and detailed specification:
- https://www.histdata.com/f-a-q/
- https://www.histdata.com/f-a-q/data-files-detailed-specification/

## Prepare data
Download EUR/USD -> 1 Minute Bar Data -> Generic ASCII from HistData, extract the monthly CSV, then run:
```bash
python prepare_histdata_m15.py DAT_ASCII_EURUSD_M1_2024.csv EURUSD_M15_UTC.csv
```
The converter rejects malformed, duplicate, unordered, non-finite, or inconsistent rows. It aggregates UTC quarter-hour buckets and keeps only buckets containing all 15 M1 rows.

## Important comparability warning
HistData is an independent provider, not RoboForex. Its bid bars, fixed EST timestamps, price construction and sessions may differ from RoboForex MT4. UTC quarter-hour boundaries may also differ from the broker server's chart boundaries. Do not call this a RoboForex backtest. For final EA validation, export M1 history from the actual RoboForex demo terminal and preserve broker server timestamps/timezone, then align the bars to that server's M15 boundaries.

The HistData site says its free data is supplied without warranty. Treat it as a development dataset, not certified market data.
