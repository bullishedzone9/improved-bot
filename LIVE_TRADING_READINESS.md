# Live Trading Readiness — SILKOUS Forex Intelligence

## Current verified status

- Repository: `bullishedzone9/improved-bot`
- Existing application: Streamlit research dashboard with historical CSV analysis, an illustrative moving-average backtest, and a third-party quote snapshot.
- The dashboard currently has **no broker connection and no order-execution path**.
- Repository search did not find an MT4 Expert Advisor, MT4 bridge, broker adapter, or order-execution module.
- GitHub Actions passed on the last verified commit, but passing CI does not establish trading readiness.
- No Vercel project matching this repository was found. A public Streamlit deployment URL has not been verified.
- The user has previously reported an Exness MT4 account and a desktop-tested EA; those external components have not been inspected or end-to-end verified from this repository.

## Required staged path

### Stage 0 — Recover and inspect the MT4 EA
- Obtain the exact EA source (`.mq4`) or compiled file plus its settings and test evidence.
- Inspect all network destinations, DLL imports, file access, order functions, symbol mapping, lot sizing, stop-loss/take-profit behavior, retry behavior, and logging.
- Do not place real-money orders during this stage.

### Stage 1 — Build a secure bridge in demo-only mode
- Use an HTTPS endpoint and a server-side secret store; never commit broker passwords, API keys, tokens, or signing secrets.
- Authenticate each EA request; validate schema, timestamp/expiry, nonce, and idempotency key.
- Reject replayed, stale, malformed, duplicate, or unauthorized commands.
- Use the broker terminal's own symbol and quote data for execution checks. A third-party snapshot is not an executable-price source.
- Start with read-only health/quote/status messages. Do not expose an unauthenticated endpoint that can issue orders.
- Keep order submission disabled by default and explicitly restrict initial testing to an Exness demo account.

### Stage 2 — Mandatory risk controls before any demo order
- Hard cap on trade risk, lot size, open positions, and daily loss.
- Require a valid stop-loss for every entry; reject trades when sizing or stop distance cannot be validated.
- Enforce maximum spread, allowed symbols, trading sessions, and a stale-quote threshold.
- Add duplicate-order protection, bounded retries, audit logs, emergency kill switch, and safe behavior on disconnect.
- Confirm whether the EA or bridge is the single authority for risk checks; never rely only on a dashboard slider.

### Stage 3 — End-to-end demo verification
- Verify EA → HTTPS bridge → validation/risk checks → MT4/Exness demo terminal → broker acknowledgement → persisted audit record.
- Test rejects for expired requests, bad authentication, duplicate requests, invalid symbol/volume, missing stop-loss, excessive spread, daily-loss cap, and network interruption.
- Verify order state and fills against the MT4 terminal, not merely an HTTP success response.
- Run a sustained demo soak test and reconcile all requested, accepted, rejected, and filled orders.

### Stage 4 — Live-mode release gate
Live execution remains **disabled** until all earlier stages pass and the user explicitly approves the final live-mode switch after reviewing risk limits and test evidence. A successful build, dashboard deployment, or demo trade alone is not sufficient.

## Immediate next action

Supply or link the actual MT4 EA source and its current configuration (remove account numbers, passwords, investor/master passwords, and all secrets first). The repository currently does not contain those components, so the bridge cannot safely be wired to the real EA yet.
