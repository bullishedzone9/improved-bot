# ARC_SILK MT4 bridge integration design

## Scope of this stage

The existing `mt4/ARC_SILK_MT4_Bridge.mq4` exporter is read-only. This document specifies the next integration stage; it does not claim that the service is deployed or connected.

## Required topology

```
Exness MT4 desktop / VPS
  └─ ARC_SILK MT4 EA (read-only telemetry)
       └─ authenticated HTTPS POST (future stage)
            └─ bridge API (future stage)
                 └─ Streamlit dashboard reads status and latest quote
```

The Streamlit dashboard must not collect or store the broker password. Do not put API secrets, passwords, account IDs, or personal account data in GitHub, source files, query strings, or logs.

## Protocol contract (proposed)

A future bridge endpoint should accept a JSON payload with:
- `schema_version`: fixed protocol version
- `event_time`: UTC ISO-8601 timestamp
- `broker_server_time`: MT4 server timestamp
- `symbol`: allowlisted symbol
- `bid`, `ask`, `spread_points`: finite positive numeric values; ask must be >= bid
- `sequence`: monotonic counter per EA instance

The bridge should add its own `received_at` timestamp. The dashboard must label broker time and receive time separately, reject future-dated or stale events, and show DISCONNECTED/STALE rather than reusing old quotes as live.

## Security requirements before network activation

- HTTPS only; authenticate every request with a revocable per-installation credential.
- Keep credentials in terminal-side configuration and server-side secret storage, never in source control.
- Add request size limits, schema validation, rate limits, replay/sequence checks, and redacted logs.
- Do not expose an unauthenticated public endpoint that accepts arbitrary payloads.
- Do not transmit balance/equity by default; add an explicit opt-in if account metrics are later needed.
- Start with quote-only telemetry. Do not add order-command endpoints in this stage.

## Acceptance tests

1. Valid payload is accepted and server receive time is recorded.
2. Missing fields, malformed JSON, invalid symbol, non-finite prices, crossed quote, and oversized body are rejected.
3. Expired/invalid authentication is rejected.
4. Replayed sequence and stale timestamps are flagged/rejected.
5. Dashboard displays quote age and connection state; stale data cannot be labelled live.
6. Service restart and network outage result in a visible disconnected state.
7. Automated tests use synthetic fixtures only and never contact a broker or place orders.

## Deployment note

The Streamlit app is hosted separately from MT4. A small authenticated HTTPS service is needed for a reliable bridge; Streamlit itself should not be treated as a persistent broker-side execution process. Deploy the bridge separately only after its authentication and tests are implemented.
