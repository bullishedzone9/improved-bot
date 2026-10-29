"""MT4-free, signal-only EMA/ATR engine for cloud paper testing.

This module never sends orders or connects to a broker. Candle rows must be
ordered oldest-to-newest and represent completed bars.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Sequence


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite positive number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite positive number") from exc
    if not isfinite(result) or result <= 0:
        raise ValueError(f"{label} must be a finite positive number")
    return result


def validate_candles(candles: Sequence[dict[str, Any]]) -> list[dict[str, float]]:
    """Validate OHLC bars, preserving oldest-to-newest order."""
    if not isinstance(candles, (list, tuple)) or not candles:
        raise ValueError("candles must be a non-empty list of OHLC rows")
    result: list[dict[str, float]] = []
    for index, candle in enumerate(candles):
        if not isinstance(candle, dict):
            raise ValueError(f"candle {index} must be an object")
        row = {key: _number(candle.get(key), f"candle {index} {key}")
               for key in ("open", "high", "low", "close")}
        if row["high"] < max(row["open"], row["close"], row["low"]):
            raise ValueError(f"candle {index} has inconsistent high")
        if row["low"] > min(row["open"], row["close"], row["high"]):
            raise ValueError(f"candle {index} has inconsistent low")
        result.append(row)
    return result


def ema(values: Sequence[float], period: int) -> list[float | None]:
    """EMA seeded with the first period's simple moving average."""
    if isinstance(period, bool) or not isinstance(period, int) or period < 2:
        raise ValueError("period must be an integer >= 2")
    if len(values) < period:
        return [None] * len(values)
    vals = [_number(v, "EMA input") for v in values]
    out: list[float | None] = [None] * len(vals)
    seed = sum(vals[:period]) / period
    out[period - 1] = seed
    alpha = 2.0 / (period + 1.0)
    previous = seed
    for i in range(period, len(vals)):
        previous = alpha * vals[i] + (1.0 - alpha) * previous
        out[i] = previous
    return out


def atr(candles: Sequence[dict[str, float]], period: int) -> list[float | None]:
    """Simple-average ATR over true ranges; first bar uses high-low."""
    if isinstance(period, bool) or not isinstance(period, int) or period < 1:
        raise ValueError("ATR period must be an integer >= 1")
    true_ranges: list[float] = []
    previous_close: float | None = None
    for row in candles:
        high, low, close = row["high"], row["low"], row["close"]
        true_ranges.append(high - low if previous_close is None else
                           max(high - low, abs(high - previous_close), abs(low - previous_close)))
        previous_close = close
    out: list[float | None] = [None] * len(true_ranges)
    for i in range(period - 1, len(true_ranges)):
        out[i] = sum(true_ranges[i - period + 1:i + 1]) / period
    return out


def evaluate_signal(
    candles: Sequence[dict[str, Any]],
    *,
    fast_period: int = 20,
    slow_period: int = 50,
    atr_period: int = 14,
    stop_atr_multiple: float = 2.0,
    reward_risk_ratio: float = 2.0,
) -> dict[str, Any]:
    """Return the latest completed-bar crossover signal; never place an order."""
    rows = validate_candles(candles)
    if isinstance(fast_period, bool) or not isinstance(fast_period, int) or fast_period < 2:
        raise ValueError("fast_period must be an integer >= 2")
    if isinstance(slow_period, bool) or not isinstance(slow_period, int) or slow_period <= fast_period:
        raise ValueError("slow_period must be an integer greater than fast_period")
    if isinstance(atr_period, bool) or not isinstance(atr_period, int) or atr_period < 1:
        raise ValueError("atr_period must be an integer >= 1")
    stop_multiple = float(stop_atr_multiple)
    rr = float(reward_risk_ratio)
    if not isfinite(stop_multiple) or stop_multiple <= 0 or not isfinite(rr) or rr <= 0:
        raise ValueError("stop ATR multiple and reward/risk ratio must be positive finite numbers")
    if len(rows) < max(slow_period, atr_period) + 1:
        raise ValueError(f"need at least {max(slow_period, atr_period) + 1} completed candles")

    closes = [row["close"] for row in rows]
    fast = ema(closes, fast_period)
    slow = ema(closes, slow_period)
    atr_values = atr(rows, atr_period)
    i = len(rows) - 1
    prior_fast, current_fast = fast[i - 1], fast[i]
    prior_slow, current_slow = slow[i - 1], slow[i]
    if None in (prior_fast, current_fast, prior_slow, current_slow, atr_values[i]):
        raise ValueError("indicator warm-up is incomplete")

    direction = "FLAT"
    if prior_fast <= prior_slow and current_fast > current_slow:
        direction = "BUY"
    elif prior_fast >= prior_slow and current_fast < current_slow:
        direction = "SELL"
    atr_value = float(atr_values[i])
    stop_distance = atr_value * stop_multiple
    return {
        "mode": "PAPER_ONLY",
        "symbol": "unspecified",
        "signal": direction,
        "bar_index": i,
        "close": closes[i],
        "fast_ema": float(current_fast),
        "slow_ema": float(current_slow),
        "atr": atr_value,
        "stop_distance": stop_distance,
        "target_distance": stop_distance * rr,
        "order_sent": False,
    }
