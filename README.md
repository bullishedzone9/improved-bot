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

## Automated checks

GitHub Actions runs Python compilation and a Streamlit startup smoke test on pushes and pull requests targeting `main`. See [the workflow](.github/workflows/python-checks.yml).

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for the recommended Streamlit hosting route and post-deployment verification checklist. A commit to GitHub does not mean the application is deployed.

## MT4 connection (optional)

The dashboard is **local-first**: CSV research, demo calculations, and the external market-data snapshot do not require a bridge token. The MT4 EA can also export quote snapshots to a local MT4 CSV file with HTTP disabled.

Use the separate read-only HTTPS bridge only if MT4 is running on another machine and its quotes must be sent to this hosted dashboard. In that remote setup, the server-side bearer token protects the network endpoint from unauthorized quote submissions; it is not a trading credential and does not enable order execution. Keep `EnableHttpBridge=false` unless the bridge has been deliberately deployed and configured. Never put a token in source control or chat.

The current MT4 EA is a **read-only telemetry exporter**, not an automated order-execution bot. It has not yet been compiled or end-to-end tested in a real MT4 terminal, and no broker connection is claimed. Live order execution remains disabled.

## Important safety boundary

**Paper analysis only.** This project does not connect to a broker, execute orders, or provide personalized financial advice. Moving-average comparisons are unvalidated descriptive candidates, not guaranteed signals. The illustrative risk budget does not calculate position size or account for leverage, spreads, fees, slippage, or execution risk. Test with sample data before relying on outputs.

## Current scope

This is an early-stage analysis dashboard, not a production trading system. Authentication, persistent storage, automated market-data feeds, and backtesting are not implemented.
