# ARC_SILK MT4 bridge integration design

## Current scope

The MT4 Expert Advisor can optionally POST quote-only telemetry to the separate authenticated bridge over HTTPS. HTTP posting is disabled by default. The EA never places, modifies, or closes orders. The service must be deployed separately and the terminal must be explicitly configured before data can flow.

## Topology

MT4 desktop/VPS -> read-only EA -> authenticated HTTPS POST /mt4/telemetry -> bridge API -> authenticated GET /mt4/latest -> Streamlit dashboard.

The dashboard must not collect or store the broker password. Never put API secrets, passwords, account IDs, or personal account data in GitHub, source files, query strings, or logs.

## Payload contract

The EA posts only schema_version (string 1), UTC ISO-8601 event_time, symbol, numeric bid/ask/spread_points, and an increasing sequence counter for the current EA run. No balance, equity, free margin, account currency, account number, or broker credentials are sent in the request body. Account metrics are disabled by default and, if enabled, remain local CSV-only.

## Enablement checklist

1. Deploy bridge_service to a service with valid HTTPS.
2. Configure ARC_SILK_BRIDGE_TOKEN as a server-side secret of at least 32 characters. Do not commit or share it.
3. In the EA's local MT4 inputs, set EnableHttpBridge=true, BridgeUrl to the HTTPS base URL, and BridgeToken to the matching token.
4. In MT4 desktop, open Tools > Options > Expert Advisors and add the exact HTTPS host to Allow WebRequest for listed URL.
5. Compile the EA in MetaEditor and attach it to a demo chart. Confirm the MT4 quote matches the bridge/dashboard and remains fresh.
6. If HTTP fails, inspect the MT4 Experts log for an error code/status. Never paste tokens or request headers into support messages.

## Security and production gaps

- HTTPS only; rotate the shared bearer token if exposed. A shared token is a prototype, not per-installation identity.
- Request size limit, authentication, schema validation, and freshness checks are implemented in the receiver.
- Replay/sequence protection and rate limiting remain required before public production use. The sequence counter resets when the EA restarts, so production replay protection needs a per-installation ID or restart-safe counter.
- Latest quote is held in process memory and disappears on service restart. This is not durable storage or an order-execution channel.
- Keep the dashboard token in server-side Streamlit secrets/environment, never browser-side code.
- No order-command endpoints in this stage.

## Acceptance tests

1. Valid synthetic payload is accepted and receive time recorded.
2. Missing fields, malformed JSON, invalid symbol, non-finite prices, crossed quote, and oversized body are rejected.
3. Missing/invalid authentication is rejected on both telemetry and latest-quote endpoints.
4. Stale timestamps are rejected and stale latest data is not labelled live.
5. Restart/network outage is displayed as disconnected.
6. Automated tests use synthetic fixtures only; no broker is contacted and no orders are placed.

## Deployment note

The Streamlit app and bridge are separate deployments. Do not call the system live-connected until the bridge is deployed over HTTPS, EA WebRequest is enabled locally, and a real quote is observed end-to-end. Use demo-only verification for any future execution work.
