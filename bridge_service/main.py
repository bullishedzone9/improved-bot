"""Small read-only receiver for MT4 quote telemetry.

Deploy as a separate HTTPS service. Set ARC_SILK_BRIDGE_TOKEN in the hosting
environment; never commit the token. Only normalized quote fields are retained.
"""
from __future__ import annotations

import hmac
import json
import os
import sqlite3
import time
from pathlib import Path
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from mt4_bridge_validation import validate_mt4_telemetry

app = FastAPI(title="ARC_SILK MT4 Read-only Bridge", version="0.1.3")
_lock = Lock()
_request_times: deque[float] = deque()
RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW_SECONDS = 60.0
MAX_BODY_BYTES = 8_192


def _db_path() -> str:
    # Production hosts must mount persistent storage and set this path explicitly.
    return os.environ.get(
        "ARC_SILK_BRIDGE_DB_PATH",
        str(Path(__file__).resolve().parent / "bridge_state.sqlite3"),
    )


def _initialize_db() -> None:
    path = _db_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path, timeout=5) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS symbol_sequences "
            "(symbol TEXT PRIMARY KEY, sequence INTEGER NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS latest_quote "
            "(id INTEGER PRIMARY KEY CHECK (id = 1), payload TEXT NOT NULL)"
        )


def _accept_and_store_quote(quote: dict[str, Any]) -> bool:
    # Commit replay state and latest quote together so a storage error cannot
    # consume a sequence without persisting the corresponding quote.
    with sqlite3.connect(_db_path(), timeout=5) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT sequence FROM symbol_sequences WHERE symbol = ?",
            (quote["symbol"],),
        ).fetchone()
        if row is not None and quote["sequence"] <= row[0]:
            conn.rollback()
            return False
        conn.execute(
            "INSERT INTO symbol_sequences(symbol, sequence) VALUES (?, ?) "
            "ON CONFLICT(symbol) DO UPDATE SET sequence = excluded.sequence",
            (quote["symbol"], quote["sequence"]),
        )
        conn.execute(
            "INSERT INTO latest_quote(id, payload) VALUES (1, ?) "
            "ON CONFLICT(id) DO UPDATE SET payload = excluded.payload",
            (json.dumps(quote, separators=(",", ":")),),
        )
        conn.commit()
    return True

def _load_latest_quote() -> dict[str, Any] | None:
    with sqlite3.connect(_db_path(), timeout=5) as conn:
        row = conn.execute("SELECT payload FROM latest_quote WHERE id = 1").fetchone()
    if row is None:
        return None
    value = json.loads(row[0])
    return value if isinstance(value, dict) else None


_initialize_db()


def _expected_token() -> str:
    token = os.environ.get("ARC_SILK_BRIDGE_TOKEN", "")
    if len(token) < 32:
        raise HTTPException(status_code=503, detail="Bridge authentication is not configured")
    return token


def _authorize(authorization: str | None) -> None:
    expected = _expected_token()
    supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health")
def health() -> dict[str, str]:
    # Public process-health endpoint; does not reveal quote/account data.
    return {"status": "ok", "mode": "read_only"}


@app.post("/mt4/telemetry")
async def receive_telemetry(
    request: Request,
    authorization: str | None = Header(default=None),
) -> JSONResponse:
    _authorize(authorization)
    # Process-local token rate limit. Configure an edge/proxy limit as well;
    # this guard resets on restart and is not a substitute for distributed limits.
    now = time.monotonic()
    with _lock:
        while _request_times and now - _request_times[0] >= RATE_LIMIT_WINDOW_SECONDS:
            _request_times.popleft()
        if len(_request_times) >= RATE_LIMIT_REQUESTS:
            raise HTTPException(status_code=429, detail="Telemetry rate limit exceeded")
        _request_times.append(now)

    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_BODY_BYTES:
                raise HTTPException(status_code=413, detail="Payload too large")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Content-Length") from None

    chunks: list[bytes] = []
    body_size = 0
    async for chunk in request.stream():
        body_size += len(chunk)
        if body_size > MAX_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Payload too large")
        chunks.append(chunk)
    body = b"".join(chunks)
    try:
        payload = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(status_code=400, detail="Invalid JSON") from None
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON object required")

    try:
        quote = validate_mt4_telemetry(payload)
    except (TypeError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=422, detail=f"Telemetry rejected: {exc}") from None

    safe_quote = {
        "schema_version": quote["schema_version"],
        "event_time": quote["event_time"],
        "symbol": quote["symbol"],
        "bid": quote["bid"],
        "ask": quote["ask"],
        "spread_points": quote["spread_points"],
        "sequence": quote["sequence"],
        "received_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        accepted = _accept_and_store_quote(safe_quote)
        if not accepted:
            raise HTTPException(status_code=409, detail="Repeated or out-of-order sequence")
    except sqlite3.Error:
        raise HTTPException(status_code=503, detail="Bridge storage unavailable") from None
    return JSONResponse({
        "accepted": True,
        "symbol": safe_quote["symbol"],
        "sequence": safe_quote["sequence"],
    })


@app.get("/mt4/latest")
def latest_quote(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _authorize(authorization)
    try:
        quote = _load_latest_quote()
    except (sqlite3.Error, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="Quote storage unavailable") from None
    if quote is None:
        raise HTTPException(status_code=404, detail="No MT4 quote received yet")
    try:
        received_at = datetime.fromisoformat(quote["received_at"])
        if received_at.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        age = (datetime.now(timezone.utc) - received_at.astimezone(timezone.utc)).total_seconds()
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=503, detail="Stored quote timestamp is invalid") from None
    if age < -5:
        raise HTTPException(status_code=503, detail="Server clock is inconsistent")
    age = max(0.0, age)
    if age > 30:
        raise HTTPException(status_code=503, detail="MT4 telemetry is stale")
    return {"connected": True, "age_seconds": round(age, 2), "quote": quote}
