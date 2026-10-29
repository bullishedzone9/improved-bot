"""Validated loader for the public third-party EURUSD H1 research dataset."""
from __future__ import annotations

import io
import requests
import pandas as pd

PUBLIC_EURUSD_H1_URL = (
    "https://huggingface.co/datasets/Yllvar/fx-historical-data/"
    "resolve/main/EURUSD/EURUSD_H1.parquet"
)
USER_AGENT = "ARC_SILK-Historical-Research/1.0"
REQUIRED_OHLC = ("open", "high", "low", "close")


def load_public_eurusd_h1(timeout: int = 45) -> pd.DataFrame:
    """Download and normalize public EURUSD H1 candles; never connects to a broker."""
    try:
        response = requests.get(
            PUBLIC_EURUSD_H1_URL,
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not download public EURUSD H1 data: {exc}") from exc

    if not response.content:
        raise ValueError("The historical-data source returned an empty file.")

    try:
        frame = pd.read_parquet(io.BytesIO(response.content))
    except Exception as exc:
        raise ValueError(f"Downloaded file is not a readable Parquet dataset: {exc}") from exc

    frame.columns = [str(column).strip().lower() for column in frame.columns]
    aliases = {
        "datetime": ("datetime", "timestamp", "date", "time", "date_time", "gmt time"),
        "open": ("open", "o", "open_price"),
        "high": ("high", "h", "high_price"),
        "low": ("low", "l", "low_price"),
        "close": ("close", "c", "close_price"),
        "volume": ("volume", "vol", "tick_volume"),
    }
    rename = {}
    for canonical, candidates in aliases.items():
        if canonical not in frame.columns:
            match = next((candidate for candidate in candidates if candidate in frame.columns), None)
            if match:
                rename[match] = canonical
    frame = frame.rename(columns=rename)

    missing = [column for column in REQUIRED_OHLC if column not in frame.columns]
    if missing:
        raise ValueError(
            "Public EURUSD dataset is missing required OHLC columns: "
            + ", ".join(missing)
            + f". Columns received: {', '.join(map(str, frame.columns))}"
        )

    for column in REQUIRED_OHLC + (("volume",) if "volume" in frame.columns else ()):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.dropna(subset=list(REQUIRED_OHLC)).copy()
    frame = frame[(frame[list(REQUIRED_OHLC)] > 0).all(axis=1)].copy()
    invalid = (
        (frame["high"] < frame[["open", "close", "low"]].max(axis=1))
        | (frame["low"] > frame[["open", "close", "high"]].min(axis=1))
        | (frame["high"] < frame["low"])
    )
    frame = frame.loc[~invalid].copy()

    if frame.empty:
        raise ValueError("The public EURUSD dataset contains no valid positive OHLC candles.")

    date_column = next((name for name in ("datetime", "timestamp", "date", "time") if name in frame.columns), None)
    if date_column:
        parsed = pd.to_datetime(frame[date_column], errors="coerce", utc=True)
        frame = frame.loc[parsed.notna()].copy()
        frame["_source_datetime"] = parsed.loc[parsed.notna()]
        if frame.empty:
            raise ValueError("The public EURUSD dataset has no parseable timestamps.")
        if frame["_source_datetime"].duplicated().any():
            raise ValueError("The public EURUSD dataset contains duplicate timestamps.")
        frame = frame.sort_values("_source_datetime").reset_index(drop=True)
        frame["datetime"] = frame["_source_datetime"]
        if date_column != "datetime":
            frame = frame.drop(columns=[date_column], errors="ignore")
        frame = frame.drop(columns=["_source_datetime"])

    if len(frame) < 3:
        raise ValueError(f"Only {len(frame)} valid candles were received; at least 3 are required.")
    return frame
