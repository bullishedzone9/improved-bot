# ARC_SILK On-Demand Agent — Phase 2 API boundary

## What was added

A FastAPI HTTP interface exposes the signal-screening engine at `POST /v1/screen` and a public process health check at `GET /health`.

The screening endpoint:
- Requires a bearer token configured as `ARC_SILK_AGENT_API_TOKEN` (minimum 32 characters).
- Validates symbol, timeframe, OHLC values, timezone-aware candle/quote timestamps, chronological candle ordering, and quote/candle sequence.
- Calculates quote age on the server; clients cannot claim a fresh quote by supplying an age number.
- Returns a screening result and the explicit `execution: NOT_AVAILABLE` marker.
- Has no broker credentials, broker API client, order endpoint, or trade execution capability.

## Run locally

```bash
python -m pip install -r requirements.txt
export ARC_SILK_AGENT_API_TOKEN='use-a-random-secret-of-at-least-32-characters'
uvicorn on_demand_agent.api:app --host 127.0.0.1 --port 8080
```

Use a secrets manager for deployment. Never commit the token or paste it into chat. Do not bind publicly without HTTPS, authentication, request-size limits, and deployment-level rate limiting.

## Verification

```bash
python -m unittest tests.test_on_demand_agent tests.test_on_demand_api -v
```

The API is a screening interface only. It is not connected to a live market feed or RoboForex. A hosted API process does not itself make a broker connection persistent or execute orders.

## Remaining gates

1. Verify a broker-supported market-data and order-execution interface for this exact RoboForex account type.
2. Add a trusted quote/candle adapter and symbol contract metadata.
3. Run walk-forward backtests with spread, commission, swaps, and slippage.
4. Run shadow/paper tests and compare signals with broker prices.
5. Implement a separate demo-only execution adapter only after the broker route is verified.

No live trading. No martingale/grid. No credential scraping or browser automation.
