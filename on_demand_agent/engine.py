"""Fail-closed, on-demand signal screening for ARC_SILK.

This module is deliberately broker-agnostic and has NO order-execution code.
It screens completed OHLC candles and returns a candidate or a no-trade reason.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isfinite
from typing import Iterable, Mapping, Any


@dataclass(frozen=True)
class ScreeningConfig:
    fast_ema: int = 20
    slow_ema: int = 50
    atr_period: int = 14
    atr_stop_multiple: float = 2.0
    reward_risk: float = 2.0
    risk_percent: float = 0.25
    daily_loss_limit_percent: float = 1.0
    max_spread_points: float = 25.0
    max_quote_age_seconds: float = 30.0

    def validate(self) -> None:
        if self.fast_ema < 2 or self.slow_ema <= self.fast_ema:
            raise ValueError("EMA periods must satisfy 2 <= fast < slow")
        if self.atr_period < 2 or self.atr_stop_multiple <= 0 or self.reward_risk <= 0:
            raise ValueError("ATR and reward/risk settings must be positive")
        if not 0 < self.risk_percent <= 0.25:
            raise ValueError("risk_percent must be in (0, 0.25]")
        if not 0 < self.daily_loss_limit_percent <= 1.0:
            raise ValueError("daily_loss_limit_percent must be in (0, 1.0]")
        if self.max_spread_points <= 0 or self.max_quote_age_seconds <= 0:
            raise ValueError("spread and quote-age limits must be positive")


@dataclass(frozen=True)
class ScreeningResult:
    status: str
    reason: str
    direction: str | None = None
    entry_reference: float | None = None
    stop_reference: float | None = None
    target_reference: float | None = None
    atr: float | None = None
    risk_percent: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _ema(values: list[float], period: int) -> list[float]:
    alpha = 2.0 / (period + 1.0)
    result = [values[0]]
    for value in values[1:]:
        result.append(alpha * value + (1.0 - alpha) * result[-1])
    return result


def _true_ranges(candles: list[Mapping[str, float]]) -> list[float]:
    ranges: list[float] = []
    previous_close: float | None = None
    for candle in candles:
        high, low, close = (float(candle[k]) for k in ("high", "low", "close"))
        tr = high - low
        if previous_close is not None:
            tr = max(tr, abs(high - previous_close), abs(low - previous_close))
        ranges.append(tr)
        previous_close = close
    return ranges


def _no_trade(reason: str) -> ScreeningResult:
    return ScreeningResult(status="NO_TRADE", reason=reason)


def screen_market(
    candles: Iterable[Mapping[str, float]],
    *,
    bid: float,
    ask: float,
    quote_age_seconds: float,
    spread_points: float,
    point: float,
    daily_loss_percent: float,
    config: ScreeningConfig = ScreeningConfig(),
) -> ScreeningResult:
    """Return a closed-candle EMA/ATR candidate; never places an order."""
    config.validate()
    try:
        rows = list(candles)
        if len(rows) < max(config.slow_ema + 2, config.atr_period + 1):
            return _no_trade("INSUFFICIENT_CLOSED_CANDLES")
        numeric = [float(x[k]) for x in rows for k in ("high", "low", "close")]
        if not all(isfinite(x) for x in numeric):
            return _no_trade("NON_FINITE_CANDLE_DATA")
        if any(float(row["high"]) < max(float(row["low"]), float(row["close"])) or
               float(row["low"]) > min(float(row["high"]), float(row["close"]))
               for row in rows):
            return _no_trade("INVALID_OHLC_RANGE")
        if any(float(rows[i]["close"]) <= 0 for i in range(len(rows))):
            return _no_trade("INVALID_CLOSE")
        if not all(isfinite(float(x)) for x in (bid, ask, quote_age_seconds, spread_points, point, daily_loss_percent)):
            return _no_trade("NON_FINITE_MARKET_STATE")
    except (KeyError, TypeError, ValueError):
        return _no_trade("INVALID_MARKET_DATA")

    if bid <= 0 or ask < bid or point <= 0:
        return _no_trade("INVALID_QUOTE")
    if quote_age_seconds < 0 or quote_age_seconds > config.max_quote_age_seconds:
        return _no_trade("STALE_QUOTE")
    if spread_points < 0 or spread_points > config.max_spread_points:
        return _no_trade("SPREAD_TOO_WIDE")
    if daily_loss_percent >= config.daily_loss_limit_percent:
        return _no_trade("DAILY_LOSS_LOCK")

    closes = [float(x["close"]) for x in rows]
    fast = _ema(closes, config.fast_ema)
    slow = _ema(closes, config.slow_ema)
    direction: str | None = None
    if fast[-2] <= slow[-2] and fast[-1] > slow[-1]:
        direction = "BUY"
    elif fast[-2] >= slow[-2] and fast[-1] < slow[-1]:
        direction = "SELL"
    if direction is None:
        return _no_trade("NO_CLOSED_CANDLE_CROSSOVER")

    atr_values = _true_ranges(rows)
    atr = sum(atr_values[-config.atr_period:]) / config.atr_period
    if not isfinite(atr) or atr <= 0:
        return _no_trade("INVALID_ATR")

    entry = ask if direction == "BUY" else bid
    stop_distance = atr * config.atr_stop_multiple
    stop = entry - stop_distance if direction == "BUY" else entry + stop_distance
    target_distance = stop_distance * config.reward_risk
    target = entry + target_distance if direction == "BUY" else entry - target_distance
    return ScreeningResult(
        status="CANDIDATE",
        reason="CLOSED_CANDLE_CROSSOVER_AND_RISK_FILTERS_PASSED",
        direction=direction,
        entry_reference=entry,
        stop_reference=stop,
        target_reference=target,
        atr=atr,
        risk_percent=config.risk_percent,
    )
