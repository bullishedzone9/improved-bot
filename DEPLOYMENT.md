# Deployment guide

## Hosting

This repository runs a Streamlit application. Use Streamlit Community Cloud (or another host that supports persistent Streamlit processes); Vercel's standard static/serverless deployment model is not a direct fit.

1. Sign in to Streamlit Community Cloud with the GitHub account that can access `bullishedzone9/improved-bot`.
2. Open the app's settings and confirm the repository is `bullishedzone9/improved-bot`, branch `main`, and main file `app.py`.
3. A connected Streamlit app normally detects commits on the configured branch and rebuilds. If it does not, open the Streamlit app dashboard and reboot the app.
4. Wait for the build to complete, then open the deployed app URL and run the smoke tests below.

## Smoke tests

- Confirm the ARC_SILK / SILKOUS Forex Intelligence header and paper-analysis warning appear.
- In **Live Forex market snapshot**, choose a major pair and press **Refresh live quote**. Confirm a quote is displayed, with provider timestamp or explicit notice if the provider omits one.
- If the provider is unavailable, confirm the app displays an error and does not silently substitute simulated prices.
- Select the built-in simulated demo data and confirm the moving-average chart and historical backtest render. The demo data is explicitly simulated and is not a live quote.
- Upload a CSV with at least 50 positive numeric close prices and confirm the chart and summary render.
- Test a malformed CSV and a CSV without a `close` column; the app should show a useful error instead of crashing.

## Data and safety notes

- Live snapshot integration uses the public BiQuote endpoint documented at `https://biquote.io/api/{SYMBOL}`. Provider availability, quote coverage, timestamps, latency, and licensing are external dependencies and must be validated in the hosted environment.
- The snapshot is not guaranteed to match a broker's executable bid/ask. It is not an execution feed and does not place orders.
- Historical backtesting remains separate from the live quote snapshot; the live snapshot does not automatically feed live candles into the backtest.
- Do not add broker credentials or private keys to source code or CSV files. If credentials are needed later, use the host's secret manager.
- Keep GitHub Actions checks passing before release.
- A deployment is not considered verified until the host build succeeds and the hosted app is manually smoke-tested.


## Live quote validation

- Live quote payloads are normalized by `live_quotes.py`; malformed JSON, non-positive/non-finite prices, ambiguous multi-row responses, and crossed bid/ask values are rejected.
- When the provider supplies a parseable market timestamp, quotes older than 180 seconds or more than 30 seconds in the future are rejected. This threshold is a conservative application check, not a guarantee of market-data quality.
- If the provider omits its market timestamp, the quote is visibly marked as freshness-unverified. It must not be treated as a verified live quote.
- Unit tests cover valid ISO/Unix timestamps, missing timestamps, stale/future timestamps, crossed prices, and malformed responses.
- The app's retrieval timestamp records when this server fetched the payload; it is not a substitute for the provider's market timestamp.
