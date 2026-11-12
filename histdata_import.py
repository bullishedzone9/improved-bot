"""Import HistData Generic ASCII M1 bars and resample complete UTC M15 bars."""
from __future__ import annotations

from pathlib import Path
import pandas as pd


COLUMNS = ["source_datetime_est", "open", "high", "low", "close", "volume"]


def load_histdata_m1(path: str | Path) -> tuple[pd.DataFrame, dict]:
    """Parse no-header semicolon M1 data; HistData timestamps are fixed EST (UTC-5)."""
    try:
        raw = pd.read_csv(path, sep=";", header=None, names=COLUMNS, dtype=str)
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise ValueError(f"Unable to read HistData M1 CSV: {exc}") from exc
    if raw.empty:
        raise ValueError("HistData file is empty")
    if raw.shape[1] != 6:
        raise ValueError("Expected six semicolon-separated fields per row")
    # HistData publishes EST without DST. Fixed UTC-5 means add exactly five hours.
    naive = pd.to_datetime(raw["source_datetime_est"].str.strip(),
                           format="%Y%m%d %H%M%S", errors="coerce")
    if naive.isna().any():
        raise ValueError("Invalid HistData timestamp; expected YYYYMMDD HHMMSS")
    if (naive.dt.second != 0).any():
        raise ValueError("HistData M1 timestamps must be aligned to whole minutes (seconds=00)")
    if naive.duplicated().any():
        raise ValueError("Duplicate HistData minute timestamps")
    if not naive.is_monotonic_increasing:
        raise ValueError("HistData rows must be chronological")
    frame = pd.DataFrame({"date": (naive + pd.Timedelta(hours=5)).dt.tz_localize("UTC")})
    for col in ("open", "high", "low", "close", "volume"):
        frame[col] = pd.to_numeric(raw[col], errors="coerce")
        if frame[col].isna().any():
            raise ValueError(f"HistData {col} contains invalid values")
    prices = frame[["open", "high", "low", "close"]]
    if not (prices.to_numpy() > 0).all():
        raise ValueError("OHLC prices must be positive")
    if (frame.high < frame[["open", "low", "close"]].max(axis=1)).any():
        raise ValueError("Invalid OHLC high")
    if (frame.low > frame[["open", "high", "close"]].min(axis=1)).any():
        raise ValueError("Invalid OHLC low")
    if (frame.volume < 0).any():
        raise ValueError("Volume must be non-negative")
    return frame, {
        "source": "HistData Generic ASCII M1",
        "source_timezone": "EST fixed UTC-5, no DST",
        "normalized_timezone": "UTC",
        "rows": int(len(frame)),
        "start_utc": frame.date.iloc[0].isoformat(),
        "end_utc": frame.date.iloc[-1].isoformat(),
    }


def resample_complete_m15(m1: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Aggregate only M15 buckets containing all 15 consecutive M1 bars."""
    if not {"date", "open", "high", "low", "close", "volume"}.issubset(m1.columns):
        raise ValueError("M1 frame is missing required columns")
    data = m1.set_index("date").sort_index()
    if data.index.has_duplicates or not data.index.is_monotonic_increasing:
        raise ValueError("M1 timestamps must be unique and chronological")
    # A count of 15 alone is insufficient if timestamps are offset; require every
    # exact minute boundary within each UTC quarter-hour bucket.
    second_offsets = data.index.second
    if (second_offsets != 0).any():
        raise ValueError("M1 timestamps must be aligned to whole minutes")
    grouped = data.resample("15min", label="left", closed="left")
    result = grouped.agg(
        open=("open", "first"), high=("high", "max"), low=("low", "min"),
        close=("close", "last"), volume=("volume", "sum"),
        minute_count=("close", "count"),
    )
    complete = result[result.minute_count == 15].drop(columns=["minute_count"])
    if complete.empty:
        raise ValueError("No complete 15-minute buckets found; provide continuous M1 history")
    output = complete.reset_index().rename(columns={"index": "date"})
    return output, {
        "m1_rows": int(len(data)),
        "m15_complete_bars": int(len(output)),
        "m15_incomplete_buckets_dropped": int(len(result) - len(complete)),
        "m15_start_utc": output.date.iloc[0].isoformat(),
        "m15_end_utc": output.date.iloc[-1].isoformat(),
        "aggregation": "UTC quarter-hour buckets; incomplete buckets dropped",
    }
