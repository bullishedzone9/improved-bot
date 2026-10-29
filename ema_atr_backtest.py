"""Historical, signal-only EMA/ATR backtest. No broker connection or order execution."""
from __future__ import annotations

from typing import Any, Sequence

from paper_engine import atr, ema, validate_candles


def backtest_ema_atr(
    candles: Sequence[dict[str, Any]],
    *,
    fast_period: int = 20,
    slow_period: int = 50,
    atr_period: int = 14,
    stop_atr_multiple: float = 2.0,
    reward_risk_ratio: float = 2.0,
    cost_bps_per_side: float = 2.0,
    max_holding_bars: int = 100,
) -> dict[str, Any]:
    """Test crossovers using next-bar-open entries and conservative OHLC exits.

    Only one position may be open. If stop and target both fall inside a candle,
    stop is assumed first. Any position still open at the data end is closed at
    the final close. Costs are deducted per side as a fraction of entry/exit price.
    """
    rows = validate_candles(candles)
    if isinstance(fast_period, bool) or not isinstance(fast_period, int) or fast_period < 2:
        raise ValueError("fast_period must be an integer >= 2")
    if isinstance(slow_period, bool) or not isinstance(slow_period, int) or slow_period <= fast_period:
        raise ValueError("slow_period must be an integer greater than fast_period")
    if isinstance(atr_period, bool) or not isinstance(atr_period, int) or atr_period < 1:
        raise ValueError("atr_period must be an integer >= 1")
    if isinstance(max_holding_bars, bool) or not isinstance(max_holding_bars, int) or max_holding_bars < 1:
        raise ValueError("max_holding_bars must be an integer >= 1")
    stop_mult, rr, cost_bps = float(stop_atr_multiple), float(reward_risk_ratio), float(cost_bps_per_side)
    if not all(__import__("math").isfinite(x) for x in (stop_mult, rr, cost_bps)):
        raise ValueError("stop, reward/risk, and costs must be finite")
    if stop_mult <= 0 or rr <= 0 or cost_bps < 0:
        raise ValueError("stop and reward/risk must be positive; costs cannot be negative")
    minimum = max(slow_period, atr_period) + 2
    if len(rows) < minimum:
        raise ValueError(f"need at least {minimum} completed candles")

    closes = [row["close"] for row in rows]
    fast, slow, atr_values = ema(closes, fast_period), ema(closes, slow_period), atr(rows, atr_period)
    trades: list[dict[str, Any]] = []
    i = 1
    while i < len(rows):
        if None in (fast[i - 1], fast[i], slow[i - 1], slow[i], atr_values[i]):
            i += 1
            continue
        side = None
        if fast[i - 1] <= slow[i - 1] and fast[i] > slow[i]:
            side = "BUY"
        elif fast[i - 1] >= slow[i - 1] and fast[i] < slow[i]:
            side = "SELL"
        entry_index = i + 1
        if side is None or entry_index >= len(rows):
            i += 1
            continue

        entry = rows[entry_index]["open"]
        distance = float(atr_values[i]) * stop_mult
        stop = entry - distance if side == "BUY" else entry + distance
        target = entry + distance * rr if side == "BUY" else entry - distance * rr
        exit_index, exit_price, reason = min(entry_index + max_holding_bars - 1, len(rows) - 1), None, "TIME"
        last_check = exit_index
        for j in range(entry_index, exit_index + 1):
            bar = rows[j]
            if side == "BUY":
                stop_hit, target_hit = bar["low"] <= stop, bar["high"] >= target
            else:
                stop_hit, target_hit = bar["high"] >= stop, bar["low"] <= target
            if stop_hit:
                exit_index, exit_price, reason = j, stop, "STOP"
                break
            if target_hit:
                exit_index, exit_price, reason = j, target, "TARGET"
                break
        if exit_price is None:
            exit_price = rows[exit_index]["close"]
        gross = (exit_price - entry) / entry if side == "BUY" else (entry - exit_price) / entry
        cost = 2.0 * cost_bps / 10000.0
        net = gross - cost
        trades.append({
            "side": side, "signal_index": i, "entry_index": entry_index,
            "exit_index": exit_index, "entry": entry, "stop": stop, "exit": exit_price,
            "exit_reason": reason, "gross_return_pct": gross * 100,
            "cost_pct": cost * 100, "net_return_pct": net * 100,
        })
        i = exit_index + 1

    wins = sum(t["net_return_pct"] > 0 for t in trades)
    total = sum(t["net_return_pct"] for t in trades)
    gross_wins = sum(t["net_return_pct"] for t in trades if t["net_return_pct"] > 0)
    gross_losses = abs(sum(t["net_return_pct"] for t in trades if t["net_return_pct"] < 0))
    profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else (float("inf") if gross_wins > 0 else 0.0)
    # Trade-by-trade compounded equity curve, normalized to 1.0 starting capital.
    equity = peak = 1.0
    max_drawdown_pct = 0.0
    for trade in trades:
        equity *= max(0.0, 1.0 + trade["net_return_pct"] / 100.0)
        peak = max(peak, equity)
        if peak > 0:
            max_drawdown_pct = max(max_drawdown_pct, (peak - equity) / peak * 100.0)
    compounded_return_pct = (equity - 1.0) * 100.0
    return {
        "mode": "PAPER_BACKTEST_ONLY",
        "order_sent": False,
        "bars": len(rows),
        "trades": trades,
        "trade_count": len(trades),
        "win_rate_pct": (wins / len(trades) * 100) if trades else 0.0,
        "net_return_sum_pct": total,
        "average_net_return_pct": total / len(trades) if trades else 0.0,
        "profit_factor": profit_factor,
        "max_drawdown_pct": max_drawdown_pct,
        "compounded_return_pct": compounded_return_pct,
        "cost_bps_per_side": cost_bps,
        "assumptions": [
            "Crossover evaluated on completed bars; entry at next bar open.",
            "If stop and target are both touched in one bar, stop is assumed first.",
            "No overlapping positions; no spread model beyond configured cost estimate.",
            "net_return_sum_pct is the arithmetic sum; compounded_return_pct and max_drawdown_pct use a simplified sequential trade equity curve.",
            "No broker execution, position sizing, financing, or guarantee of future results.",
        ],
    }
