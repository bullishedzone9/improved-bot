"""Fail-closed acceptance gates for research-only strategy evaluation.

These gates do not predict profitability or enable execution. They reject a
candidate when required evidence is missing or thresholds are not met.
"""
from __future__ import annotations

from math import isfinite
from typing import Any


DEFAULT_THRESHOLDS = {
    "min_profit_factor": 1.20,
    "max_drawdown_pct": 10.0,
    "max_risk_per_trade_pct": 0.5,
    "max_daily_loss_pct": 2.0,
}


def evaluate_strategy_gates(
    *,
    profit_factor: float | None,
    max_drawdown_pct: float | None,
    out_of_sample_return_pct: float | None,
    risk_per_trade_pct: float,
    daily_loss_limit_pct: float,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Return a transparent PASS/FAIL checklist; missing evidence always fails.

    Returns are percentage points (e.g. 2.5 means +2.5%). Drawdown, risk and
    daily-loss inputs are positive magnitudes. This is a research gate only.
    """
    limits = {**DEFAULT_THRESHOLDS, **(thresholds or {})}
    for name, value in limits.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not isfinite(value):
            raise ValueError(f"{name} must be a finite number")
        if value < 0:
            raise ValueError(f"{name} cannot be negative")

    def finite_or_missing(value: float | None, name: str) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
            raise ValueError(f"{name} must be a finite number or None")
        return float(value)

    pf = finite_or_missing(profit_factor, "profit_factor")
    dd = finite_or_missing(max_drawdown_pct, "max_drawdown_pct")
    oos = finite_or_missing(out_of_sample_return_pct, "out_of_sample_return_pct")
    risk = finite_or_missing(risk_per_trade_pct, "risk_per_trade_pct")
    daily = finite_or_missing(daily_loss_limit_pct, "daily_loss_limit_pct")
    assert risk is not None and daily is not None

    checks = [
        {
            "name": "Profit factor",
            "value": pf,
            "requirement": f"> {limits['min_profit_factor']:.2f}",
            "passed": pf is not None and pf > limits["min_profit_factor"],
        },
        {
            "name": "Maximum drawdown",
            "value": dd,
            "requirement": f"<= {limits['max_drawdown_pct']:.2f}%",
            "passed": dd is not None and 0 <= dd <= limits["max_drawdown_pct"],
        },
        {
            "name": "Out-of-sample return after costs",
            "value": oos,
            "requirement": "> 0%",
            "passed": oos is not None and oos > 0,
        },
        {
            "name": "Risk per trade",
            "value": risk,
            "requirement": f"<= {limits['max_risk_per_trade_pct']:.2f}%",
            "passed": 0 <= risk <= limits["max_risk_per_trade_pct"],
        },
        {
            "name": "Daily loss stop",
            "value": daily,
            "requirement": f"<= {limits['max_daily_loss_pct']:.2f}%",
            "passed": 0 < daily <= limits["max_daily_loss_pct"],
        },
    ]
    failed = [check["name"] for check in checks if not check["passed"]]
    return {
        "mode": "RESEARCH_GATE_ONLY",
        "passed": not failed,
        "execution_allowed": False,
        "checks": checks,
        "failed_checks": failed,
        "note": (
            "A pass means only that supplied metrics meet these provisional "
            "thresholds. It does not prove future profitability or authorize live trading."
        ),
    }
