"""Small read-only receiver for MT4 quote telemetry.

Deploy as a separate HTTPS service. Set ARC_SILK_BRIDGE_TOKEN in the hosting
environment; never commit the token. Only normalized quote fields are retained.
"""
from __future__ import annotations

import hmac
import os
import time
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from mt4_bridge_validation import validate_mt4_telemetry

app = FastAPI(title="ARC_SILK MT4 Read-only Bridge", version="0.1.1")
_lock = Lock()
_latest: dict[str, Any] | None = None
_received_monotonic: float | None = None
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
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Payload too large")
    try:
        payload = await request.json()
    except Exception:
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
        _latest = safe_quote
        _received_monotonic = time.monotonic()
    return JSONResponse({"accepted": True, "symbol": safe_quote["symbol"], "sequence": safe_quote["sequence"]})


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
