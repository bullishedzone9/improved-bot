"""Small read-only receiver for MT4 quote telemetry.

Deploy as a separate HTTPS service. Set ARC_SILK_BRIDGE_TOKEN in the hosting
environment; never commit the token. Only normalized quote fields are retained.
"""
from __future__ import annotations

import hmac
import json
import os
import time
from collections import deque
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from mt4_bridge_validation import validate_mt4_telemetry

app = FastAPI(title="ARC_SILK MT4 Read-only Bridge", version="0.1.2")
_lock = Lock()
_latest: dict[str, Any] | None = None
_received_monotonic: float | None = None
_last_sequence_by_symbol: dict[str, int] = {}
_request_times: deque[float] = deque()
RATE_LIMIT_REQUESTS = 60
RATE_LIMIT_WINDOW_SECONDS = 60.0
MAX_BODY_BYTES = 8_192


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

    # Read incrementally so a chunked request cannot force an unbounded body
    # allocation before the payload-size limit is enforced.
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
    global _latest, _received_monotonic
    with _lock:
        previous_sequence = _last_sequence_by_symbol.get(safe_quote["symbol"])
        if previous_sequence is not None and safe_quote["sequence"] <= previous_sequence:
            raise HTTPException(status_code=409, detail="Repeated or out-of-order sequence")
        _last_sequence_by_symbol[safe_quote["symbol"]] = safe_quote["sequence"]
        _latest = safe_quote
        _received_monotonic = time.monotonic()
    return JSONResponse({
        "accepted": True,
        "symbol": safe_quote["symbol"],
        "sequence": safe_quote["sequence"],
    })


@app.get("/mt4/latest")
def latest_quote(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    _authorize(authorization)
    with _lock:
        quote = dict(_latest) if _latest else None
        received = _received_monotonic
    if quote is None or received is None:
        raise HTTPException(status_code=404, detail="No MT4 quote received yet")
    age = max(0.0, time.monotonic() - received)
    if age > 30:
        raise HTTPException(status_code=503, detail="MT4 telemetry is stale")
    return {"connected": True, "age_seconds": round(age, 2), "quote": quote}
