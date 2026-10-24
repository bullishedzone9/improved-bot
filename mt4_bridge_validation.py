"""Validation for read-only ARC_SILK MT4 telemetry payloads.

This module validates telemetry only; it has no broker connectivity or order APIs.
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any


class TelemetryValidationError(ValueError):
    """Raised when an MT4 telemetry payload is unsafe or unusable."""


def _parse_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise TelemetryValidationError("event_time must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TelemetryValidationError("event_time is not valid ISO-8601") from exc
    if parsed.tzinfo is None:
        raise TelemetryValidationError("event_time must include a timezone")
    return parsed.astimezone(timezone.utc)


def _finite_positive(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise TelemetryValidationError(f"{field} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise TelemetryValidationError(f"{field} must be numeric") from exc
    if not math.isfinite(number) or number <= 0:
        raise TelemetryValidationError(f"{field} must be finite and positive")
    return number


def validate_mt4_telemetry(
    payload: dict[str, Any],
    *,
    allowed_symbols: set[str] | None = None,
    now: datetime | None = None,
    max_age_seconds: int = 30,
) -> dict[str, Any]:
    """Validate and normalize one quote telemetry event.

    Account metrics are intentionally ignored; the returned object contains
    quote telemetry only. Caller must authenticate the sender separately.
    """
    if not isinstance(payload, dict):
        raise TelemetryValidationError("payload must be an object")
    if payload.get("schema_version") != "1":
        raise TelemetryValidationError("unsupported schema_version")

    symbol = payload.get("symbol")
    if not isinstance(symbol, str) or not symbol.strip():
        raise TelemetryValidationError("symbol is required")
    symbol = symbol.strip().upper()
    if allowed_symbols is not None and symbol not in allowed_symbols:
        raise TelemetryValidationError("symbol is not allowlisted")

    bid = _finite_positive(payload.get("bid"), "bid")
    ask = _finite_positive(payload.get("ask"), "ask")
    if ask < bid:
        raise TelemetryValidationError("ask must be greater than or equal to bid")

    spread_points = payload.get("spread_points")
    if isinstance(spread_points, bool):
        raise TelemetryValidationError("spread_points must be numeric")
    try:
        spread_points = float(spread_points)
    except (TypeError, ValueError) as exc:
        raise TelemetryValidationError("spread_points must be numeric") from exc
    if not math.isfinite(spread_points) or spread_points < 0:
        raise TelemetryValidationError("spread_points must be finite and non-negative")

    sequence = payload.get("sequence")
    if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
        raise TelemetryValidationError("sequence must be a non-negative integer")

    event_time = _parse_time(payload.get("event_time"))
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise TelemetryValidationError("now must include a timezone")
    age = (current.astimezone(timezone.utc) - event_time).total_seconds()
    if age < -5:
        raise TelemetryValidationError("event_time is too far in the future")
    if age > max_age_seconds:
        raise TelemetryValidationError("telemetry is stale")

    return {
        "schema_version": "1",
        "event_time": event_time.isoformat(),
        "symbol": symbol,
        "bid": bid,
        "ask": ask,
        "spread_points": spread_points,
        "sequence": sequence,
        "age_seconds": max(0.0, age),
        "fresh": True,
    }
