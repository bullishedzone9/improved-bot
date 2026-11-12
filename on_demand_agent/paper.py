"""Deterministic paper-trade simulator. Never connects to a broker or places orders."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Iterable, Mapping, Any


@dataclass(frozen=True)
class PaperResult:
    status: str
    reason: str
    direction: str | None = None
    entry_price: float | None = None
    exit_price: float | None = None
    exit_reason: str | None = None
    bars_held: int = 0
    risk_amount: float | None = None
    gross_r: float | None = None
    costs_r: float | None = None
    net_r: float | None = None
    pnl: float | None = None
    ending_equity: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _rejected(reason: str) -> PaperResult:
    return PaperResult(status="REJECTED", reason=reason)


def simulate_paper_trade(
    *,
    direction: str,
    stop_price: float,
    target_price: float,
    future_candles: Iterable[Mapping[str, float]],
    starting_equity: float,
    risk_percent: float = 0.25,
    daily_loss_percent: float = 0.0,
    daily_loss_limit_percent: float = 1.0,
    costs_r: float = 0.0,
) -> PaperResult:
    """Enter at the first future candle open; use conservative stop-first intrabar handling.

    costs_r is a caller-supplied aggregate estimate of spread, commission and slippage
    expressed in initial-risk units. It is subtracted from gross R, not inferred.
    """
    if not isinstance(direction, str) or direction not in {"BUY", "SELL"}:
        return _rejected("INVALID_DIRECTION")
    try:
        stop_price, target_price, starting_equity, risk_percent, daily_loss_percent, daily_loss_limit_percent, costs_r = (
            float(value) for value in (stop_price, target_price, starting_equity, risk_percent,
                                       daily_loss_percent, daily_loss_limit_percent, costs_r)
        )
    except (TypeError, ValueError, OverflowError):
        return _rejected("NON_NUMERIC_INPUT")
    values = (stop_price, target_price, starting_equity, risk_percent,
              daily_loss_percent, daily_loss_limit_percent, costs_r)
    if not all(isfinite(value) for value in values):
        return _rejected("NON_FINITE_INPUT")
    if starting_equity <= 0 or not 0 < risk_percent <= 0.25:
        return _rejected("INVALID_EQUITY_OR_RISK")
    if not 0 < daily_loss_limit_percent <= 1.0 or daily_loss_percent < 0:
        return _rejected("INVALID_DAILY_LOSS_CONFIGURATION")
    if daily_loss_percent >= daily_loss_limit_percent:
        return _rejected("DAILY_LOSS_LOCK")
    if costs_r < 0 or costs_r > 1.0:
        return _rejected("INVALID_COST_ESTIMATE")

    try:
        candles = list(future_candles)
        if not candles:
            return _rejected("NO_FUTURE_CANDLES")
        for candle in candles:
            high, low, open_price, close = (
                float(candle[k]) for k in ("high", "low", "open", "close")
            )
            if not all(isfinite(x) and x > 0 for x in (high, low, open_price, close)):
                return _rejected("INVALID_CANDLE_DATA")
            if high < max(low, open_price, close) or low > min(high, open_price, close):
                return _rejected("INVALID_OHLC_RANGE")
    except (KeyError, TypeError, ValueError):
        return _rejected("INVALID_CANDLE_DATA")

    entry = float(candles[0]["open"])
    stop = float(stop_price)
    target = float(target_price)
    if direction == "BUY":
        if not stop < entry < target:
            return _rejected("INVALID_BUY_LEVELS_OR_GAP_PAST_TARGET")
        initial_risk = entry - stop
    else:
        if not target < entry < stop:
            return _rejected("INVALID_SELL_LEVELS_OR_GAP_PAST_TARGET")
        initial_risk = stop - entry
    if initial_risk <= 0:
        return _rejected("INVALID_INITIAL_RISK")

    exit_price: float | None = None
    exit_reason = "END_OF_DATA"
    bars_held = 0
    for index, candle in enumerate(candles, start=1):
        high, low, open_price = float(candle["high"]), float(candle["low"]), float(candle["open"])
        bars_held = index
        if direction == "BUY":
            if open_price <= stop:
                exit_price, exit_reason = open_price, "STOP_GAP"
                break
            if low <= stop and high >= target:
                exit_price, exit_reason = stop, "STOP_FIRST_BOTH_TOUCHED"
                break
            if low <= stop:
                exit_price, exit_reason = stop, "STOP_LOSS"
                break
            if high >= target:
                exit_price, exit_reason = target, "TAKE_PROFIT"
                break
        else:
            if open_price >= stop:
                exit_price, exit_reason = open_price, "STOP_GAP"
                break
            if low <= target and high >= stop:
                exit_price, exit_reason = stop, "STOP_FIRST_BOTH_TOUCHED"
                break
            if high >= stop:
                exit_price, exit_reason = stop, "STOP_LOSS"
                break
            if low <= target:
                exit_price, exit_reason = target, "TAKE_PROFIT"
                break

    if exit_price is None:
        exit_price = float(candles[-1]["close"])
    signed_move = (exit_price - entry) if direction == "BUY" else (entry - exit_price)
    gross_r = signed_move / initial_risk
    net_r = gross_r - costs_r
    risk_amount = starting_equity * (risk_percent / 100.0)
    pnl = risk_amount * net_r
    ending_equity = starting_equity + pnl
    return PaperResult(
        status="SIMULATED",
        reason="PAPER_ONLY_NO_BROKER_ORDER",
        direction=direction,
        entry_price=entry,
        exit_price=exit_price,
        exit_reason=exit_reason,
        bars_held=bars_held,
        risk_amount=risk_amount,
        gross_r=gross_r,
        costs_r=costs_r,
        net_r=net_r,
        pnl=pnl,
        ending_equity=ending_equity,
    )
