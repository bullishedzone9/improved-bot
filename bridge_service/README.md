# ARC_SILK MT4 read-only bridge

This service is separate from the Streamlit dashboard. It accepts validated
quote telemetry from MT4 over HTTPS and exposes the most recent quote to
authorized dashboard/backend components. It does not place, modify, or close
orders.

## Configuration

- Deploy this directory as a separate Python web service with HTTPS.
- Install dependencies from `bridge_service/requirements.txt`.
- Configure `ARC_SILK_BRIDGE_TOKEN` as a secret environment variable. Use a
  randomly generated token of at least 32 characters. Never commit it or paste
  it into chat.
- The receiver expects a Bearer token in the Authorization header.
- Do not expose the token in browser-side Streamlit code. Keep it in server-side
  environment secrets only.

## Endpoints

- `GET /health`: process health only; it does not prove MT4 is connected.
- `POST /mt4/telemetry`: authenticated quote telemetry receiver.
- `GET /mt4/latest`: latest quote in memory, marked unavailable if older than
  30 seconds.

## Payload contract

JSON object with `schema_version`, timezone-aware ISO `event_time`,
`symbol`, positive `bid` and `ask` (ask must be >= bid), non-negative
`spread_points`, and monotonically increasing integer `sequence`. The
validation module rejects stale/future timestamps and invalid fields.

## Limitations before production

- The current MT4 EA exports local CSV; it does not yet POST to this service.
- Latest quote storage is in process memory and resets on restart. Use a
  managed store only if persistence is actually required.
- Add per-installation credentials, sequence replay protection, rate limits,
  and deployment-specific monitoring before public production use.
- Use demo accounts and verify quotes against the MT4 terminal before any
  trading-related decision. No order execution is implemented.
