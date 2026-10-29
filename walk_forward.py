"""Chronological train/test evaluation for the research-only EMA/ATR strategy.

This module deliberately does not optimize parameters. It separates a historical
sample chronologically and reports raw price-return and illustrative risk-sized
account metrics so raw price returns are not confused with account returns.
Execution is never enabled.
"""
from __future__ import annotations

from typing import Any, Sequence

from ema_atr_backtest import backtest_ema_atr
from risk_accounting import calculate_risk_normalized_equity


def evaluate_chronological_split(
    candles: Sequence[dict[str, Any]],
    *,
    train_fraction: float = 0.70,
    fast_period: int = 20,
    slow_period: int = 50,
    atr_period: int = 14,
    cost_bps_per_side: float = 2.0,
    risk_per_trade_pct: float = 0.25,
) -> dict[str, Any]:
    """Run fixed parameters on chronological train/test segments."""
    if isinstance(train_fraction, bool) or not isinstance(train_fraction, (int, float)):
        raise ValueError("train_fraction must be a number between 0.5 and 0.9")
    if not 0.5 <= float(train_fraction) <= 0.9:
        raise ValueError("train_fraction must be between 0.5 and 0.9")
    if isinstance(risk_per_trade_pct, bool) or not isinstance(risk_per_trade_pct, (int, float)):
        raise ValueError("risk_per_trade_pct must be a positive finite number")
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
        risk = calculate_risk_normalized_equity(
            result["trades"], risk_per_trade_pct=float(risk_per_trade_pct)
        )
        return {
            "bars": result["bars"],
            "trade_count": result["trade_count"],
            "win_rate_pct": result["win_rate_pct"],
            "profit_factor": result["profit_factor"],
            "max_drawdown_pct": result["max_drawdown_pct"],
            "net_return_sum_pct": result["net_return_sum_pct"],
            "compounded_return_pct": result["compounded_return_pct"],
            "cost_bps_per_side": result["cost_bps_per_side"],
            "risk_normalized_win_rate_pct": risk["win_rate_pct"],
            "risk_normalized_profit_factor": risk["profit_factor"],
            "risk_normalized_max_drawdown_pct": risk["max_drawdown_pct"],
            "risk_normalized_compounded_return_pct": risk["compounded_return_pct"],
            "risk_per_trade_pct": risk["risk_per_trade_pct"],
            "risk_normalized_mode": risk["mode"],
        }

    return {
        "mode": "RESEARCH_WALK_FORWARD_ONLY",
        "order_sent": False,
        "execution_allowed": False,
        "train_fraction": float(train_fraction),
        "risk_per_trade_pct": float(risk_per_trade_pct),
        "split_index": split,
        "train": summarize(train),
        "out_of_sample": summarize(test),
        "caveats": [
            "Chronological split; no random shuffling.",
            "Parameters are held fixed across both segments; this function does not tune them.",
            "Indicators initialize within each segment, so this is a simple baseline split, not a full rolling walk-forward simulation.",
            "Risk-normalized returns use initial stop distance as a proxy, not broker-grade lot sizing.",
            "Losses can exceed the initial risk budget due to time exits, gaps, and unmodelled costs.",
            "Out-of-sample results are historical evidence only and do not guarantee future profitability.",
            "Costs are simplified estimates and do not fully model broker spread, slippage, commission, swaps, or gaps.",
        ],
    }
