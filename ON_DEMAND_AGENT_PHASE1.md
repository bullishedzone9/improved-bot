# ARC_SILK On-Demand Agent — Phase 1

## Purpose

This is a phone-friendly, broker-agnostic screening engine. It evaluates a supplied batch of completed OHLC candles and a current quote snapshot, then returns either a trade candidate or a fail-closed no-trade reason.

**It does not connect to RoboForex, hold broker credentials, submit orders, or run continuously.** It is a tested decision component, not an autonomous live-trading service.

## Current screening rules

- Closed-candle EMA(20)/EMA(50) crossover; no intrabar signal.
- ATR(14) stop reference with 2R target reference.
- Quote age <= 30 seconds.
- Spread <= 25 points (must be calibrated per symbol/account).
- Daily loss lock at 1%.
- Risk budget capped at 0.25% per candidate.
- Invalid, stale, incomplete, or unsafe input returns NO_TRADE.

The engine deliberately has no order-execution function. A CANDIDATE is not an instruction to place an order.

## Why this does not yet trade without a VPS

A bot needs a live source of prices and a broker-authorized order route. RoboForex's official public VPS documentation describes a Windows Server/RDP host for Expert Advisors; the standard VPS requires account equity above $300, with a $5/month fallback when volume conditions are not met. This user has said they cannot meet the $300 equity requirement and does not want to pay for a VPS.

We have not verified a supported public RoboForex retail REST API for MT4 order execution. Third-party claims of hosted MT4 API access are not sufficient grounds to give a service trading credentials. WebTrader access to an MT4 account does not itself prove support for programmatic EA execution.

Therefore Phase 1 is intentionally limited to a deterministic screening engine and tests. Phase 2 requires confirmation of a broker-supported API or another execution route that the account holder explicitly authorizes. Do not scrape WebTrader, automate browser clicks, or send MT4 passwords to an unverified provider.

## Run tests

```bash
python -m unittest tests.test_on_demand_agent -v
```

## Next gates

1. Verify RoboForex account entity and written API/execution options with official support.
2. Connect a trustworthy market-data source; enforce timestamps and symbol/contract metadata.
3. Add historical walk-forward tests with spread, commission, swaps and slippage.
4. Run shadow/paper signals and compare them with broker quotes.
5. Only after these gates pass, implement a demo-only execution adapter with hard-coded live-account refusal and explicit operator enablement.

## Non-negotiable safety

No live orders. No martingale/grid. No trading to qualify for VPS volume. No credentials in GitHub, chat, logs, or the dashboard. A stop-loss reference cannot guarantee maximum loss during gaps or slippage.
