"""Chronological in-sample / out-of-sample evaluation for the existing SMA strategy.

No parameter search is performed: parameters are fixed by the caller to reduce
selection bias. The out-of-sample segment starts with the final training bar
as a signal warm-up row; only subsequent returns belong to the test window.
"""
from __future__ import annotations

from math import floor, isfinite
from typing import Any

import numpy as np
import pandas as pd

from backtest import run_moving_average_backtest


def _summary(result: dict[str, Any]) -> dict[str, Any]:
    trades = [float(value) for value in result["trade_returns"]]
    gains = sum(value for value in trades if value > 0)
    losses = -sum(value for value in trades if value < 0)
    profit_factor = gains / losses if losses > 0 else (None if gains == 0 else float("inf"))
    periods = result["strategy_period_returns"].iloc[1:]
    return {
        "total_return": float(result["strategy_return"]),
        "max_drawdown": float(result["max_drawdown"]),
        "completed_trades": len(trades),
        "win_rate": (sum(value > 0 for value in trades) / len(trades)) if trades else None,
        "profit_factor": profit_factor,
        "positive_periods": int((periods > 0).sum()),
        "negative_periods": int((periods < 0).sum()),
        "periods": int(len(periods)),
    }


def evaluate_walk_forward(
    close: pd.Series,
    *,
    fast_window: int = 20,
    slow_window: int = 50,
    train_fraction: float = 0.70,
    cost_bps: float = 2.0,
) -> dict[str, Any]:
    """Evaluate fixed SMA parameters on a chronological holdout.

    This is a single holdout split, not rolling multi-fold validation. Supply
    real broker-quality OHLC data and realistic all-in costs before interpreting
    results. The current strategy is long-or-cash, not a short-selling system.
    """
    if isinstance(fast_window, bool) or not isinstance(fast_window, int) or fast_window < 2:
        raise ValueError("fast_window must be an integer >= 2")
    if isinstance(slow_window, bool) or not isinstance(slow_window, int) or slow_window <= fast_window:
        raise ValueError("slow_window must be an integer greater than fast_window")
    if isinstance(train_fraction, bool) or not isinstance(train_fraction, (int, float)):
        raise ValueError("train_fraction must be between 0.5 and 0.9")
    if not isfinite(float(train_fraction)) or not 0.5 <= float(train_fraction) <= 0.9:
        raise ValueError("train_fraction must be between 0.5 and 0.9")

    prices = pd.to_numeric(pd.Series(close).reset_index(drop=True), errors="coerce")
    if len(prices) < max(slow_window * 3, 60):
        raise ValueError("Insufficient history: need at least max(slow_window * 3, 60) bars")
    values = prices.to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("close prices must be finite, numeric, and positive")

    split = floor(len(prices) * float(train_fraction))
    if split < slow_window + 2 or len(prices) - split < 10:
        raise ValueError("Training or out-of-sample segment is too short")

    fast = prices.rolling(fast_window, min_periods=fast_window).mean()
    slow = prices.rolling(slow_window, min_periods=slow_window).mean()

    train = run_moving_average_backtest(
        prices.iloc[:split], fast.iloc[:split], slow.iloc[:split], cost_bps
    )
    # Include the last training close as the prior signal bar. Its own return
    # is not counted in the OOS report because position[0] is always flat.
    test = run_moving_average_backtest(
        prices.iloc[split - 1:], fast.iloc[split - 1:], slow.iloc[split - 1:], cost_bps
    )
    return {
        "status": "RESEARCH_ONLY",
        "strategy": "SMA_LONG_OR_CASH",
        "fast_window": fast_window,
        "slow_window": slow_window,
        "train_fraction": float(train_fraction),
        "bars_total": len(prices),
        "train_bars": split,
        "out_of_sample_bars": len(prices) - split,
        "cost_bps_per_side": float(cost_bps),
        "in_sample": _summary(train),
        "out_of_sample": _summary(test),
        "warning": "One chronological holdout only; not proof of future performance. No broker execution.",
    }
