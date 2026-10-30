"""Authenticated, read-only HTTP interface for ARC_SILK signal screening.

No broker connectivity or order execution is implemented here.
"""
from __future__ import annotations

import hmac
import os
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from on_demand_agent.engine import ScreeningConfig, screen_market

app = FastAPI(
    title="ARC_SILK On-Demand Signal Screening API",
    version="0.1.0",
    description="Read-only signal screening. This service cannot place broker orders.",
)


class Candle(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    time: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float | None = Field(default=None, ge=0)


class ScreenRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    symbol: str = Field(min_length=3, max_length=24, pattern=r"^[A-Za-z0-9._-]+$")
    timeframe: Literal["M5", "M15", "M30", "H1", "H4", "D1"]
    candles: list[Candle] = Field(min_length=1, max_length=500)
    bid: float = Field(gt=0)
    ask: float = Field(gt=0)
    point: float = Field(gt=0)
    spread_points: float = Field(ge=0)
    quote_time: datetime
    daily_loss_percent: float = Field(ge=-100, le=100)


def _require_api_token(authorization: str | None) -> None:
    expected = os.environ.get("ARC_SILK_AGENT_API_TOKEN", "")
    if len(expected) < 32:
        raise HTTPException(status_code=503, detail="Agent API authentication is not configured")
    supplied = authorization.removeprefix("Bearer ").strip() if authorization else ""
    if not supplied or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _utc_age(timestamp: datetime, now: datetime) -> float:
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("timestamp must include a timezone")
    return (now - timestamp.astimezone(timezone.utc)).total_seconds()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "mode": "screening_only", "order_execution": "disabled"}


@app.post("/v1/screen")
def screen(request: ScreenRequest, authorization: str | None = Header(default=None)) -> dict:
    _require_api_token(authorization)
    now = datetime.now(timezone.utc)
    try:
        quote_age = _utc_age(request.quote_time, now)
        candle_times = [c.time for c in request.candles]
        if any(t.tzinfo is None or t.utcoffset() is None for t in candle_times):
            raise ValueError("every candle timestamp must include a timezone")
        if any(candle_times[i] >= candle_times[i + 1] for i in range(len(candle_times) - 1)):
            raise ValueError("candles must be strictly chronological with no duplicates")
        if candle_times[-1].astimezone(timezone.utc) >= request.quote_time.astimezone(timezone.utc):
            raise ValueError("quote timestamp must be later than the latest completed candle")
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from None

    if request.ask < request.bid:
        raise HTTPException(status_code=422, detail="ask must be greater than or equal to bid")

    result = screen_market(
        [c.model_dump() for c in request.candles],
        bid=request.bid,
        ask=request.ask,
        quote_age_seconds=quote_age,
        spread_points=request.spread_points,
        point=request.point,
        daily_loss_percent=request.daily_loss_percent,
        config=ScreeningConfig(),
    )
    return {
        "symbol": request.symbol,
        "timeframe": request.timeframe,
        "evaluated_at": now.isoformat(),
        "result": result.to_dict(),
        "execution": "NOT_AVAILABLE",
    }
