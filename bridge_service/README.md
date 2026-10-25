# ARC_SILK MT4 read-only bridge

This separate service accepts validated quote telemetry from the MT4 Expert Advisor and exposes the latest quote to authorized dashboard/backend components. It does not place, modify, or close orders.

## Server configuration

- Deploy this directory as a separate Python web service with HTTPS.
- Install dependencies from `bridge_service/requirements.txt`.
- Configure `ARC_SILK_BRIDGE_TOKEN` as a server-side secret, randomly generated and at least 32 characters long. Never commit it or paste it into chat.
- The receiver expects a Bearer token in the Authorization header.
- Keep the dashboard token in server-side Streamlit secrets/environment only.

## Endpoints

- `GET /health`: public process health only; it does not prove MT4 is connected.
- `POST /mt4/telemetry`: authenticated quote telemetry receiver. Rejects payloads over 8 KiB, malformed or invalid quotes, and repeated/out-of-order sequence values for a symbol.
- `GET /mt4/latest`: authenticated latest quote, unavailable if no quote exists or the last receipt is older than 30 seconds.

## MT4 EA setup

1. Compile `mt4/ARC_SILK_MT4_Bridge.mq4` using MetaEditor in the MT4 desktop terminal.
2. Leave `EnableHttpBridge=false` until the HTTPS service is deployed and configured.
3. Once ready, set `EnableHttpBridge=true`, set `BridgeUrl` to the HTTPS base URL, and enter the matching `BridgeToken` locally. Never commit the token.
4. In MT4 desktop, open Tools > Options > Expert Advisors and add the bridge's exact HTTPS host to Allow WebRequest for listed URL.
5. Attach the EA to a demo chart and verify the displayed quote against MT4. The EA sends only symbol, bid, ask, spread, UTC event time, schema version, and sequence.
6. If WebRequest fails, check the MT4 Experts log for an error code/status. The EA is designed not to print credentials.

## Payload contract

JSON object with `schema_version`, timezone-aware ISO `event_time`, `symbol`, positive `bid` and `ask` (ask must be >= bid), non-negative `spread_points`, and integer `sequence`. The validation module rejects stale/future timestamps and invalid fields.

## Known limitations before production

- HTTP transmission is opt-in and disabled by default.
- Sequence replay protection is currently in process memory and is scoped by symbol. It rejects repeated or lower sequence values while the service process is running, but a service restart resets this state; durable per-installation identity and replay protection are still required before production use.
- Latest quote storage and freshness state are process memory and reset on restart.
- Add per-installation credentials, rate limits, request-size controls at the hosting proxy, and deployment monitoring before public production use.
- Use demo accounts and verify quotes against the MT4 terminal before any trading-related decision. No order execution is implemented.
