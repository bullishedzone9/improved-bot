"""Small, offline parsers for user-supplied historical candle files."""
from __future__ import annotations

import gzip
import json
from io import BytesIO, StringIO
from typing import Any

import pandas as pd


def load_historical_upload(filename: str, payload: bytes) -> pd.DataFrame:
    """Load a CSV or gzip-compressed JSON OHLC file into normalized columns.

    Supports EV Trading Labs-style JSON rows: ts (Unix seconds), o, h, l, c,
    and optional v. The parser does not download data or connect to a broker.
    """
    name = filename.lower()
    if name.endswith(".json.gz") or name.endswith(".gz"):
        try:
            raw = gzip.decompress(payload)
            decoded: Any = json.loads(raw.decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Could not read this gzip JSON file; check the download is complete.") from exc
        if isinstance(decoded, dict):
            # Accept common wrappers around a candle array.
            for key in ("data", "candles", "results", "bars"):
                if isinstance(decoded.get(key), list):
                    decoded = decoded[key]
                    break
        if not isinstance(decoded, list) or not decoded or not all(isinstance(row, dict) for row in decoded):
            raise ValueError("Gzip JSON must contain a non-empty array of candle objects.")
        frame = pd.DataFrame(decoded)
        frame.columns = [str(col).strip().lower() for col in frame.columns]
        aliases = {"o": "open", "h": "high", "l": "low", "c": "close", "v": "volume"}
        frame = frame.rename(columns={old: new for old, new in aliases.items() if old in frame.columns and new not in frame.columns})
        if "ts" in frame.columns and not any(col in frame.columns for col in ("date", "datetime", "timestamp", "time")):
            ts = pd.to_numeric(frame["ts"], errors="coerce")
            if ts.isna().any():
                raise ValueError("The 'ts' field must contain Unix timestamps in seconds.")
            frame["date"] = pd.to_datetime(ts, unit="s", utc=True, errors="coerce")
        return frame

    try:
        return pd.read_csv(StringIO(payload.decode("utf-8-sig")))
    except (UnicodeDecodeError, pd.errors.ParserError) as exc:
        raise ValueError("Could not parse this CSV file; check its encoding and delimiter.") from exc
