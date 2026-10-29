"""Chronological train/test evaluation for the research-only EMA/ATR strategy.

This module deliberately does not optimize parameters. It separates a historical
sample chronologically and reports both segments so in-sample results cannot be
mistaken for out-of-sample evidence. Execution is never enabled.
"""
from __future__ import annotations

from typing import Any, Sequence

from ema_atr_backtest import backtest_ema_atr


def evaluate_chronological_split(
    candles: Sequence[dict[str, Any]],
    *,
    train_fraction: float = 0.70,
    fast_period: int = 20,
    slow_period: int = 50,
    atr_period: int = 14,
    cost_bps_per_side: float = 2.0,
) -> dict[str, Any]:
    """Run the same fixed parameters on chronological train and test segments."""
    if isinstance(train_fraction, bool) or not isinstance(train_fraction, (int, float)):
        raise ValueError("train_fraction must be a number between 0.5 and 0.9")
    if not 0.5 <= float(train_fraction) <= 0.9:
        raise ValueError("train_fraction must be between 0.5 and 0.9")
    rows = list(candles)
    minimum = max(slow_period, atr_period) + 2
    if len(rows) < minimum * 2:
        raise ValueError(f"need at least {minimum * 2} candles to evaluate both segments")
    split = int(len(rows) * float(train_fraction))
    if split < minimum or len(rows) - split < minimum:
        raise ValueError("train and test segments must each contain enough candles")

    common = {
        "fast_period": fast_period,
        "slow_period": slow_period,
        "atr_period": atr_period,
        "cost_bps_per_side": cost_bps_per_side,
    }
    train = backtest_ema_atr(rows[:split], **common)
    test = backtest_ema_atr(rows[split:], **common)

    def summarize(result: dict[str, Any]) -> dict[str, Any]:
        return {
            "bars": result["bars"],
            "trade_count": result["trade_count"],
            "win_rate_pct": result["win_rate_pct"],
            "profit_factor": result["profit_factor"],
            "max_drawdown_pct": result["max_drawdown_pct"],
            "net_return_sum_pct": result["net_return_sum_pct"],
            "compounded_return_pct": result["compounded_return_pct"],
            "cost_bps_per_side": result["cost_bps_per_side"],
        }

    return {
        "mode": "RESEARCH_WALK_FORWARD_ONLY",
        "order_sent": False,
        "execution_allowed": False,
        "train_fraction": float(train_fraction),
        "split_index": split,
        "train": summarize(train),
        "out_of_sample": summarize(test),
        "caveats": [
            "Chronological split; no random shuffling.",
            "Parameters are held fixed across both segments; this function does not tune them.",
            "Indicators initialize within each segment, so this is a simple baseline split, not a full rolling walk-forward simulation.",
            "Out-of-sample results are historical evidence only and do not guarantee future profitability.",
            "Costs are simplified estimates and do not fully model broker spread, slippage, commission, swaps, or gaps.",
        ],
    }
