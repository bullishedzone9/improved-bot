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

Two separate MT4 Expert Advisors are provided:
- `mt4/ARC_SILK_MT4_Bridge.mq4`: read-only quote telemetry exporter; HTTP is disabled by default.
- `mt4/ARC_SILK_AutoTrader.mq4`: an initial demo-only EMA crossover prototype using closed candles, ATR-based stop-loss, reward/risk target, 0.5% maximum configured risk per trade, 2% daily equity-loss lock, spread/margin checks, and one open position per symbol/magic number. It has no martingale, grid, or order-modification/closure logic.

The automated trader refuses to initialize on a non-demo account and starts with `EnableDemoTrading=false`. Keep that default until you have compiled it in MetaEditor and completed Strategy Tester plus broker demo forward tests. The Python CI check is only a source-level safety regression check; it does **not** compile MQL4, validate profitability, or confirm broker execution. No broker connection or deployment of the trading EA is claimed.

## Important safety boundary

**Research and demo-only prototype.** The Streamlit dashboard remains analysis-only. The separate MT4 EA can submit orders only after it is compiled and explicitly enabled on an MT4 demo account; it hard-blocks non-demo accounts. The strategy is unvalidated and may lose money. Never assume the configured stop guarantees the maximum loss: gaps, slippage, broker execution, and contract specifications can increase losses. Test with historical data and demo forward tests; live trading is not enabled or authorized.

## Current scope

This is an early-stage analysis dashboard, not a production trading system. Authentication, persistent storage, automated market-data feeds, and backtesting are not implemented.
