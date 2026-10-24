"""Pure calculations for a historical long-or-cash moving-average backtest."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


def run_moving_average_backtest(
    close: pd.Series,
    fast_ma: pd.Series,
    slow_ma: pd.Series,
    cost_bps: float = 2.0,
) -> dict[str, Any]:
    """Run a close-to-close SMA strategy with one-bar-delayed signals.

    A signal known at close t controls exposure to the return from close t to
    close t+1. A fixed cost in basis points is charged for each entry or exit.
    The benchmark is buy-and-hold over periods where the prior bar had valid
    moving averages, so its measured window matches the strategy's warm-up.
    An open trade at the end is not counted as a completed trade.
    """
    if isinstance(cost_bps, bool) or not isinstance(cost_bps, (int, float)):
        raise ValueError("cost_bps must be a number between 0 and 100")
    if not np.isfinite(cost_bps) or not 0 <= cost_bps <= 100:
        raise ValueError("cost_bps must be a number between 0 and 100")

    # Work positionally so duplicate/nonconsecutive source indexes cannot
    # corrupt trade segmentation. Inputs are expected to represent matching rows.
    close_values = pd.to_numeric(pd.Series(close).reset_index(drop=True), errors="coerce")
    fast_values = pd.to_numeric(pd.Series(fast_ma).reset_index(drop=True), errors="coerce")
    slow_values = pd.to_numeric(pd.Series(slow_ma).reset_index(drop=True), errors="coerce")
    if len(close_values) == 0:
        raise ValueError("At least one price observation is required")
    if not (len(close_values) == len(fast_values) == len(slow_values)):
        raise ValueError("Close prices and moving averages must have equal lengths")
    prices = close_values.to_numpy(dtype=float)
    if not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError("Close prices must be finite, numeric, and positive")

    fast = fast_values.to_numpy(dtype=float)
    slow = slow_values.to_numpy(dtype=float)
    fast_finite = np.isfinite(fast)
    slow_finite = np.isfinite(slow)
    # NaN is a valid warm-up marker; infinities are not valid averages.
    if np.isinf(fast).any() or np.isinf(slow).any():
        raise ValueError("Moving averages must be finite or missing")
    valid = fast_finite & slow_finite
    raw_signal = (fast > slow) & valid
    position = np.zeros(len(prices), dtype=int)
    if len(prices) > 1:
        position[1:] = raw_signal[:-1].astype(int)
        position[1:] *= valid[:-1].astype(int)

    price_returns = np.zeros(len(prices), dtype=float)
    if len(prices) > 1:
        price_returns[1:] = prices[1:] / prices[:-1] - 1.0
    eligible = np.zeros(len(prices), dtype=bool)
    if len(prices) > 1:
        eligible[1:] = valid[:-1]

    # Do not charge an entry until the first eligible return period.
    position[~eligible] = 0
    turnover = np.zeros(len(prices), dtype=float)
    if len(prices) > 1:
        turnover[1:] = np.abs(np.diff(position))
    cost_rate = float(cost_bps) / 10000.0
    strategy_returns = position * price_returns - turnover * cost_rate
    benchmark_returns = np.where(eligible, price_returns, 0.0)

    equity_values = np.cumprod(1.0 + strategy_returns)
    benchmark_values = np.cumprod(1.0 + benchmark_returns)
    equity_values /= equity_values[0]
    benchmark_values /= benchmark_values[0]
    peaks = np.maximum.accumulate(equity_values)
    drawdown_values = equity_values / peaks - 1.0

    trade_returns: list[float] = []
    entry = None
    for i, current in enumerate(position):
        previous = position[i - 1] if i else 0
        if current == 1 and previous == 0:
            entry = i
        elif current == 0 and previous == 1 and entry is not None:
            trade_returns.append(float(np.prod(1.0 + strategy_returns[entry : i + 1]) - 1.0))
            entry = None

    index = pd.RangeIndex(len(prices))
    equity = pd.Series(equity_values, index=index, name="strategy_equity")
    benchmark = pd.Series(benchmark_values, index=index, name="benchmark_equity")
    drawdown = pd.Series(drawdown_values, index=index, name="drawdown")
    strategy_periods = pd.Series(strategy_returns, index=index, name="strategy_return")
    benchmark_periods = pd.Series(benchmark_returns, index=index, name="benchmark_return")
    positions = pd.Series(position, index=index, name="position")
    return {
        "equity_curve": equity,
        "benchmark_curve": benchmark,
        "strategy_return": float(equity_values[-1] - 1.0),
        "benchmark_return": float(benchmark_values[-1] - 1.0),
        "drawdown": drawdown,
        "max_drawdown": float(drawdown_values.min()),
        "completed_trades": len(trade_returns),
        "trade_returns": trade_returns,
        "position": positions,
        "strategy_period_returns": strategy_periods,
        "benchmark_period_returns": benchmark_periods,
    }
