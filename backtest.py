"""Pure calculations for the historical moving-average backtest."""
from __future__ import annotations

from typing import Any

import pandas as pd


def run_moving_average_backtest(
    close: pd.Series,
    fast_ma: pd.Series,
    slow_ma: pd.Series,
    cost_bps: float = 2.0,
) -> dict[str, Any]:
    """Backtest a long-or-cash SMA strategy with next-bar signals and costs.

    Cost is applied to each change in position (entry or exit). Returns are
    calculated from close-to-close price changes; a signal at row t is only
    active for the return beginning at row t+1.
    """
    if not isinstance(cost_bps, (int, float)) or not 0 <= cost_bps <= 100:
        raise ValueError("cost_bps must be between 0 and 100 basis points")

    data = pd.concat(
        [
            pd.Series(close, name="close"),
            pd.Series(fast_ma, name="fast_ma"),
            pd.Series(slow_ma, name="slow_ma"),
        ],
        axis=1,
    )
    if data.empty:
        raise ValueError("At least one price observation is required")
    data = data.apply(pd.to_numeric, errors="coerce")
    prices = data["close"]
    if prices.isna().any() or (prices <= 0).any():
        raise ValueError("Close prices must be finite, numeric, and positive")
    if not prices.map(lambda value: pd.notna(value) and abs(value) != float("inf")).all():
        raise ValueError("Close prices must be finite, numeric, and positive")

    valid = data["fast_ma"].notna() & data["slow_ma"].notna()
    raw_signal = (data["fast_ma"] > data["slow_ma"]).astype(int)
    raw_signal = raw_signal.where(valid, 0)
    position = raw_signal.shift(1).fillna(0).astype(int)

    price_returns = prices.pct_change().fillna(0.0)
    # Do not include a return until both averages were available at the
    # previous close; this avoids counting the warm-up period as strategy data.
    eligible = valid.shift(1, fill_value=False)
    position = position.where(eligible, 0)
    turnover = position.diff().abs()
    if len(turnover):
        turnover.iloc[0] = abs(position.iloc[0])
    cost_rate = float(cost_bps) / 10000.0
    strategy_returns = position * price_returns - turnover.fillna(0.0) * cost_rate
    benchmark_returns = price_returns.where(eligible, 0.0)

    # First eligible return establishes the normalized start, not a price move.
    if len(strategy_returns):
        first_eligible = eligible[eligible].index[0] if eligible.any() else None
        if first_eligible is not None:
            strategy_returns.loc[first_eligible] = (
                position.loc[first_eligible] * price_returns.loc[first_eligible]
                - turnover.fillna(0.0).loc[first_eligible] * cost_rate
            )

    equity = (1.0 + strategy_returns).cumprod()
    benchmark = (1.0 + benchmark_returns).cumprod()
    if len(equity):
        equity = equity / equity.iloc[0]
        benchmark = benchmark / benchmark.iloc[0]
    peaks = equity.cummax()
    drawdown = equity / peaks - 1.0

    previous_position = position.shift(1, fill_value=0)
    exit_mask = (previous_position == 1) & (position == 0)
    exit_indices = list(exit_mask[exit_mask].index)
    trade_returns: list[float] = []
    entry_index: int | None = None
    for idx in position.index:
        if position.loc[idx] == 1 and previous_position.loc[idx] == 0:
            entry_index = position.index.get_loc(idx)
        elif position.loc[idx] == 0 and previous_position.loc[idx] == 1 and entry_index is not None:
            exit_index = position.index.get_loc(idx)
            segment = strategy_returns.iloc[entry_index : exit_index + 1]
            trade_returns.append(float((1.0 + segment).prod() - 1.0))
            entry_index = None

    strategy_total = float(equity.iloc[-1] - 1.0) if len(equity) else 0.0
    benchmark_total = float(benchmark.iloc[-1] - 1.0) if len(benchmark) else 0.0
    return {
        "equity_curve": equity,
        "benchmark_curve": benchmark,
        "strategy_return": strategy_total,
        "benchmark_return": benchmark_total,
        "drawdown": drawdown,
        "completed_trades": len(exit_indices),
        "trade_returns": trade_returns,
        "position": position,
        "strategy_period_returns": strategy_returns,
        "benchmark_period_returns": benchmark_returns,
    }
