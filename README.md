# improved-bot — ARC_SILK Forex Intelligence

A mobile-friendly Streamlit dashboard for exploratory analysis of uploaded historical forex prices.

## Features

- CSV upload with a required positive numeric `close` column.
- Optional date/time parsing and chronological sorting.
- Configurable fast and slow simple moving averages.
- Descriptive bullish/bearish/neutral trend candidates and latest-row crossover notes.
- Illustrative risk-budget arithmetic and price-series drawdown summary.
- Historical close-to-close moving-average backtest with transaction-cost assumptions.
- Quote validation helpers that reject malformed, crossed, or stale provider quotes.
- MT4-free EMA/ATR paper-signal engine for completed OHLC candles.
- Historical upload support for standard CSV and gzip-compressed JSON candles (`.json.gz`), including the `ts,o,h,l,c,v` schema used by EV Trading Labs-style archives.

## MT4-free development route

The project can continue without a Windows computer or MetaTrader 4 installation. The Python signal engine in `paper_engine.py` accepts completed OHLC candles and reports a `BUY`, `SELL`, or `FLAT` crossover candidate, ATR-based stop/target distances, and `order_sent: false`. Automated unit tests run in GitHub Actions, so development can be performed from a phone browser.

This is a **paper-signal and research workaround**, not an MT4 compiler replacement and not a broker execution connection. It does not send orders, maintain a live portfolio, or prove that the MQL4 EA compiles. The MQL4 EA remains demo-only and disabled by default. Do not enable live trading based on Python checks.

## Run locally

Python 3.10+ is recommended.

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Getting historical candles from an Android phone

For actual historical candles, use a source that clearly identifies the instrument, timeframe, date range, timezone, and data type. One option is [EV Trading Labs historical OHLCV data](https://evtradelabs.com/data), which lists downloadable EURUSD and other instrument files across timeframes. Closed-year files are listed as available without signup; current-year and M1 files may require a free account. Check the site's current access and licence terms before using its data.

1. Open the data source in your Android browser and select **EURUSD** (or the instrument you intend to study), a timeframe, and a completed calendar year.
2. Download the historical `.json.gz` file to your phone. Avoid the repository's built-in simulated demo data for performance conclusions.
3. Open the deployed ARC_SILK dashboard, choose the historical file uploader, and select the downloaded `.json.gz` file. The app normalizes `ts,o,h,l,c,v` into timestamp and OHLCV columns.
4. Confirm the displayed instrument/timeframe and date range match the file. Backtest assumptions remain approximate; bid candles, spread, commissions, slippage and broker execution can differ.
5. Save the results for research only. Do not infer live profitability from one timeframe or one date range.

The parser is an upload helper: it does not fetch files automatically, connect to a broker, or execute orders. Always use a separate out-of-sample period when comparing strategy settings.

## CSV format

A `close` column is required for the dashboard and backtest. The paper-signal engine needs OHLC rows: `open`, `high`, `low`, and `close`.

```csv
date,open,high,low,close
2026-01-01,1.1000,1.1050,1.0980,1.1030
2026-01-02,1.1030,1.1080,1.1010,1.1060
```

Rows are sorted by parsed date/time when a recognized, parseable date/time column is available; otherwise, CSV row order is used.

## Automated checks

GitHub Actions runs Python compilation, unit tests, and a Streamlit startup smoke test on pull requests targeting `main`. The MQL4 source safety workflow performs static source checks only; neither workflow is a MetaEditor compile or broker/demo execution test. See [the Python workflow](.github/workflows/python-checks.yml) and [the EA safety workflow](.github/workflows/mt4-ea-safety.yml).

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for the recommended Streamlit hosting route and post-deployment verification checklist. A commit to GitHub does not mean the application is deployed.

## Important safety boundary

**Research and paper signals only.** The Python engine does not connect to a broker or execute orders. Moving-average crossovers are unvalidated strategy signals, not guaranteed predictions. Stop/target distances are analytical estimates and do not account for contract size, pip value, spread, fees, slippage, leverage, or execution risk. Test with historical data and a demo environment before relying on any strategy.

## Current scope

This is an early-stage research dashboard and paper-signal engine, not a production trading system. The MT4 Expert Advisor is retained as a separate demo-only source artifact; MetaEditor compilation and Strategy Tester verification are still unavailable without a compatible MT4 environment.
