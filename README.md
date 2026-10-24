# improved-bot — ARC_SILK Forex Intelligence

A mobile-friendly Streamlit dashboard for exploratory analysis of uploaded historical forex prices.

## Features

- CSV upload with a required positive numeric `close` column.
- Optional date/time parsing and chronological sorting.
- Configurable fast and slow simple moving averages.
- Descriptive bullish/bearish/neutral trend candidates and latest-row crossover notes.
- Illustrative risk-budget arithmetic and price-series drawdown summary.
- Recent-observation table and basic data-quality feedback.

## Run locally

Python 3.10+ is recommended.

```bash
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## CSV format

A `close` column is required. Optional columns include `date`, `datetime`, `timestamp`, `time`, `open`, `high`, `low`, and `volume`.

```csv
date,open,high,low,close
2026-01-01,1.1000,1.1050,1.0980,1.1030
2026-01-02,1.1030,1.1080,1.1010,1.1060
```

Rows are sorted by parsed date/time when a recognized, parseable date/time column is available; otherwise, CSV row order is used.

## Important safety boundary

**Paper analysis only.** This project does not connect to a broker, execute orders, or provide personalized financial advice. Moving-average comparisons are unvalidated descriptive candidates, not guaranteed signals. The illustrative risk budget does not calculate position size or account for leverage, spreads, fees, slippage, or execution risk. Test with sample data before relying on outputs.

## Current scope

This is an early-stage analysis dashboard, not a production trading system. Authentication, persistent storage, automated market-data feeds, backtesting, and deployment configuration are not included in this version.
