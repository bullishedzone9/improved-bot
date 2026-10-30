"""Strict loader for user-supplied historical OHLC CSV data."""
from __future__ import annotations

from pathlib import Path
import pandas as pd


REQUIRED = ("date", "open", "high", "low", "close")


def load_ohlc_csv(path: str | Path) -> pd.DataFrame:
    """Load and validate chronological OHLC data; never synthesize missing bars."""
    try:
        frame = pd.read_csv(path)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise ValueError(f"Could not read OHLC CSV: {exc}") from exc
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    missing = [column for column in REQUIRED if column not in frame.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    if frame.empty:
        raise ValueError("CSV contains no price rows")

    parsed_dates = pd.to_datetime(frame["date"], errors="coerce", utc=True)
    if parsed_dates.isna().any():
        raise ValueError("date column contains invalid or missing timestamps")
    if parsed_dates.duplicated().any():
        raise ValueError("duplicate timestamps are not allowed")
    if not parsed_dates.is_monotonic_increasing:
        raise ValueError("rows must be in strictly chronological order")

    for column in ("open", "high", "low", "close"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        if frame[column].isna().any() or not frame[column].map(lambda x: pd.notna(x) and abs(x) != float("inf")).all():
            raise ValueError(f"{column} contains non-finite or non-numeric values")
        if (frame[column] <= 0).any():
            raise ValueError(f"{column} prices must be positive")

    invalid = (
        (frame["high"] < frame[["open", "close", "low"]].max(axis=1))
        | (frame["low"] > frame[["open", "close", "high"]].min(axis=1))
    )
    if invalid.any():
        raise ValueError("OHLC relationship invalid: high/low do not contain open, close and range")
    frame["date"] = parsed_dates
    return frame.reset_index(drop=True)
