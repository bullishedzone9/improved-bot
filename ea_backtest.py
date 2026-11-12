"""Research backtester approximating ARC_SILK MT4 EMA/ATR rules on OHLC bars.

Research only. Assumes CSV OHLC prices are BID prices. Entries occur at the
next bar open, with configured spread applied to BUY entry/exit. If SL and TP
are both touched within one bar, SL is assumed first (conservative).
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class EAResearchConfig:
    fast_ema: int = 20
    slow_ema: int = 50
    atr_period: int = 14
    atr_stop_multiple: float = 2.0
    reward_risk: float = 2.0
    spread_points: float = 0.0
    point: float = 0.0001
    risk_percent: float = 0.25
    max_daily_loss_percent: float = 1.0

    def validate(self) -> None:
        if self.fast_ema < 2 or self.slow_ema <= self.fast_ema:
            raise ValueError("EMA periods must satisfy 2 <= fast < slow")
        if self.atr_period < 2 or self.atr_stop_multiple <= 0 or self.reward_risk <= 0:
            raise ValueError("ATR and reward/risk settings must be positive")
        if not isfinite(self.spread_points) or self.spread_points < 0:
            raise ValueError("spread_points must be finite and >= 0")
        if not isfinite(self.point) or self.point <= 0:
            raise ValueError("point must be finite and > 0")
        if not 0 < self.risk_percent <= 0.5:
            raise ValueError("risk_percent must be in (0, 0.5]")
        if not 0 < self.max_daily_loss_percent <= 2:
            raise ValueError("max_daily_loss_percent must be in (0, 2]")


def _wilder_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int) -> pd.Series:
    prev = close.shift(1)
    tr = pd.concat([high - low, (high - prev).abs(), (low - prev).abs()], axis=1).max(axis=1)
    # MT4 iATR uses Wilder-style smoothing after its initial seed.
    return tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()


def run_ea_aligned_backtest(
    frame: pd.DataFrame, config: EAResearchConfig = EAResearchConfig()
) -> dict[str, Any]:
    """Simulate closed-bar EMA cross + ATR SL/TP with fixed fractional risk.

    Fractional risk normalizes each trade's planned stop loss to risk_percent
    of current equity. It does not model broker lot constraints or tick value.
    Daily loss is an equity lock on new entries; open trades remain open as in
    the EA's current implementation.
    """
    config.validate()
    required = ("date", "open", "high", "low", "close")
    if any(c not in frame.columns for c in required):
        raise ValueError("frame must contain date, open, high, low, close")
    data = frame.loc[:, required].copy().reset_index(drop=True)
    for col in ("open", "high", "low", "close"):
        data[col] = pd.to_numeric(data[col], errors="coerce")
    if len(data) < max(config.slow_ema * 3, config.atr_period * 3, 100):
        raise ValueError("insufficient OHLC history for EMA/ATR warmup")
    values = data[["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values <= 0).any():
        raise ValueError("OHLC values must be finite and positive")
    if (data["high"] < data[["open", "low", "close"]].max(axis=1)).any():
        raise ValueError("invalid OHLC high")
    if (data["low"] > data[["open", "high", "close"]].min(axis=1)).any():
        raise ValueError("invalid OHLC low")
    dates = pd.to_datetime(data["date"], utc=True, errors="coerce")
    if dates.isna().any() or dates.duplicated().any() or not dates.is_monotonic_increasing:
        raise ValueError("date must be valid, unique and chronological")

    fast = data.close.ewm(span=config.fast_ema, adjust=False).mean()
    slow = data.close.ewm(span=config.slow_ema, adjust=False).mean()
    atr = _wilder_atr(data.high, data.low, data.close, config.atr_period)
    spread = config.spread_points * config.point
    equity = 1.0
    peak = 1.0
    max_dd = 0.0
    day_start_equity = equity
    current_day = dates.iloc[0].date()
    locked_days: set[Any] = set()
    position = None
    trades: list[dict[str, Any]] = []

    for i in range(1, len(data)):
        day = dates.iloc[i].date()
        if day != current_day:
            current_day = day
            day_start_equity = equity

        bar = data.iloc[i]
        # Manage open position first; SL wins if both boundaries are touched.
        if position is not None:
            direction = position["direction"]
            if direction == "BUY":
                stop_hit = bar.low <= position["sl"]
                target_hit = bar.high >= position["tp"]
                exit_price = position["sl"] if stop_hit else position["tp"] if target_hit else None
                if exit_price is not None:
                    exit_price -= spread  # sell to close a long at bid
            else:
                stop_hit = bar.high >= position["sl"]
                target_hit = bar.low <= position["tp"]
                exit_price = position["sl"] if stop_hit else position["tp"] if target_hit else None
                if exit_price is not None:
                    # Short exits buy at ask; OHLC bars are bid-side.
                    exit_price += spread
            if exit_price is not None:
                gross = (exit_price - position["entry"]) if direction == "BUY" else (position["entry"] - exit_price)
                r_multiple = gross / position["stop_distance"]
                pnl_fraction = position["risk_fraction"] * r_multiple
                equity *= max(0.0, 1.0 + pnl_fraction)
                trades.append({"direction": direction, "entry_index": position["entry_index"],
                               "exit_index": i, "r_multiple": float(r_multiple),
                               "return_fraction": float(pnl_fraction),
                               "exit_reason": "STOP" if stop_hit else "TARGET"})
                position = None
                peak = max(peak, equity)
                max_dd = max(max_dd, (peak - equity) / peak)

        daily_loss = (day_start_equity - equity) / day_start_equity if day_start_equity > 0 else 1.0
        if daily_loss >= config.max_daily_loss_percent / 100.0:
            locked_days.add(day)
        if position is not None or day in locked_days or i < max(config.slow_ema, config.atr_period) + 1:
            continue

        direction = None
        if fast.iloc[i - 1] <= slow.iloc[i - 1] and fast.iloc[i] > slow.iloc[i]:
            direction = "BUY"
        elif fast.iloc[i - 1] >= slow.iloc[i - 1] and fast.iloc[i] < slow.iloc[i]:
            direction = "SELL"
        atr_value = float(atr.iloc[i])
        if direction is None or not isfinite(atr_value) or atr_value <= 0:
            continue

        # Signal is known only after bar i closes; enter at bar i+1 open.
        if i + 1 >= len(data):
            continue
        next_open = float(data.iloc[i + 1].open)
        entry = next_open + spread if direction == "BUY" else next_open
        stop_distance = atr_value * config.atr_stop_multiple
        if stop_distance <= 0:
            continue
        position = {
            "direction": direction, "entry": entry,
            "sl": entry - stop_distance if direction == "BUY" else entry + stop_distance,
            "tp": entry + stop_distance * config.reward_risk if direction == "BUY" else entry - stop_distance * config.reward_risk,
            "stop_distance": stop_distance,
            "risk_fraction": config.risk_percent / 100.0,
            "entry_index": i + 1,
        }

    returns = [t["return_fraction"] for t in trades]
    wins = [x for x in returns if x > 0]
    losses = [-x for x in returns if x < 0]
    return {
        "status": "RESEARCH_ONLY",
        "strategy": "MT4_EMA_CROSS_ATR_SL_TP_APPROXIMATION",
        "bars": len(data),
        "trades": len(trades),
        "win_rate": len(wins) / len(returns) if returns else None,
        "profit_factor": sum(wins) / sum(losses) if losses else (None if not wins else None),
        "net_return": equity - 1.0,
        "ending_equity_index": equity,
        "max_drawdown": max_dd,
        "open_position_at_end": position is not None,
        "daily_loss_locked_days": len(locked_days),
        "trade_log": trades,
        "assumptions": [
            "OHLC input is bid-side data",
            "spread is constant and applied symmetrically",
            "entries occur at next bar open after completed crossover",
            "SL is assumed before TP when both are touched in one bar",
            "risk is normalized fractionally; broker lot sizing and tick value are not modeled",
            "no commission, swap, slippage, gaps, margin or broker stop-level rules",
            "daily loss lock blocks new entries but does not close open positions",
        ],
        "warning": "Approximation for research only; validate against MT4 Strategy Tester and broker demo fills.",
    }
