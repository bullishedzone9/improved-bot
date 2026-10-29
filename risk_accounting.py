"""Risk-normalized equity accounting for historical research only.

Converts net price-return trade results into illustrative account returns using
a fixed fraction of equity at the initial stop distance. This is not
broker-grade position sizing and never authorizes order execution.
"""
from __future__ import annotations

from math import isfinite
from typing import Any, Sequence


def calculate_risk_normalized_equity(
    trades: Sequence[dict[str, Any]],
    *,
    risk_per_trade_pct: float = 0.25,
    starting_equity: float = 1.0,
) -> dict[str, Any]:
    """Calculate illustrative equity from stop-normalized trade returns.

    Each trade requires positive entry and stop prices plus net_return_pct,
    a price return percentage after estimated costs. The initial stop distance
    is a proxy for risk; losses can exceed the budget due to gaps, time exits,
    slippage, and other unmodelled execution effects.
    """
    if isinstance(risk_per_trade_pct, bool) or not isinstance(risk_per_trade_pct, (int, float)):
        raise ValueError("risk_per_trade_pct must be a finite number")
    if not isfinite(risk_per_trade_pct) or not 0 < risk_per_trade_pct <= 100:
        raise ValueError("risk_per_trade_pct must be > 0 and <= 100")
    if isinstance(starting_equity, bool) or not isinstance(starting_equity, (int, float)):
        raise ValueError("starting_equity must be a finite positive number")
    if not isfinite(starting_equity) or starting_equity <= 0:
        raise ValueError("starting_equity must be a finite positive number")

    equity = peak = float(starting_equity)
    max_drawdown_pct = 0.0
    rows: list[dict[str, Any]] = []
    positive_returns: list[float] = []
    negative_returns: list[float] = []

    for index, trade in enumerate(trades):
        try:
            entry = float(trade["entry"])
            stop = float(trade["stop"])
            net_return_pct = float(trade["net_return_pct"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"trade {index} must include numeric entry, stop, and net_return_pct") from exc
        if not all(isfinite(value) for value in (entry, stop, net_return_pct)):
            raise ValueError(f"trade {index} values must be finite")
        if entry <= 0 or stop <= 0 or entry == stop:
            raise ValueError(f"trade {index} entry and stop must be positive and different")

        stop_distance_pct = abs(entry - stop) / entry * 100.0
        account_return_pct = (net_return_pct / stop_distance_pct) * float(risk_per_trade_pct)
        growth_factor = 1.0 + account_return_pct / 100.0
        if growth_factor < 0:
            raise ValueError(
                f"trade {index} implies an account loss greater than 100%; "
                "the simplified equity model cannot represent this safely"
            )
        equity *= growth_factor
        if account_return_pct > 0:
            positive_returns.append(account_return_pct)
        elif account_return_pct < 0:
            negative_returns.append(account_return_pct)
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown_pct = max(max_drawdown_pct, (peak - equity) / peak * 100.0)
        rows.append({
            "trade_index": index,
            "stop_distance_pct": stop_distance_pct,
            "net_price_return_pct": net_return_pct,
            "account_return_pct": account_return_pct,
            "equity": equity,
        })

    gross_wins = sum(positive_returns)
    gross_losses = abs(sum(negative_returns))
    profit_factor = (
        gross_wins / gross_losses if gross_losses > 0
        else (float("inf") if gross_wins > 0 else 0.0)
    )
    return {
        "mode": "RISK_NORMALIZED_RESEARCH_ONLY",
        "execution_allowed": False,
        "starting_equity": float(starting_equity),
        "ending_equity": equity,
        "compounded_return_pct": (equity / float(starting_equity) - 1.0) * 100.0,
        "max_drawdown_pct": max_drawdown_pct,
        "risk_per_trade_pct": float(risk_per_trade_pct),
        "trade_count": len(rows),
        "win_rate_pct": (len(positive_returns) / len(rows) * 100.0) if rows else 0.0,
        "profit_factor": profit_factor,
        "trades": rows,
        "limitations": [
            "Uses initial stop distance as a proxy for account risk; not broker-grade position sizing.",
            "Assumes supplied net price return already includes estimated costs.",
            "Does not model gaps, additional slippage, commissions, swaps, margin, pip value, or partial fills.",
            "Does not enforce an intraday daily-loss stop because trades have no validated timestamps.",
            "A time exit or gap can lose more than the chosen initial risk budget.",
            "No broker connection or order execution.",
        ],
    }
