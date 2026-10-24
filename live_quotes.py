from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import Any


class QuoteValidationError(ValueError):
    """Raised when a provider response cannot be trusted as a usable quote."""


def _positive_number(payload: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(number) and number > 0:
            return number
    return None


def _parse_timestamp(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            return None
        seconds = float(value) / 1000 if value > 10_000_000_000 else float(value)
        try:
            return datetime.fromtimestamp(seconds, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def validate_quote(payload: Any, symbol: str, *, now: datetime | None = None,
                   max_age_seconds: int = 180, max_future_skew_seconds: int = 30) -> dict[str, Any]:
    """Normalize a quote and reject provider-marked, timestamped, or age-metadata stale data."""
    if isinstance(payload, list):
        if len(payload) != 1:
            raise QuoteValidationError("Expected exactly one quote in the provider response.")
        payload = payload[0]
    if not isinstance(payload, dict):
        raise QuoteValidationError("Provider response must be a JSON object.")

    stale_flag = payload.get("stale")
    if stale_flag is True or (isinstance(stale_flag, str) and stale_flag.strip().lower() in {"true", "yes", "1"}):
        raise QuoteValidationError("Provider explicitly marks this quote as stale.")
    if stale_flag is not None and not isinstance(stale_flag, (bool, str)):
        raise QuoteValidationError("Provider stale flag has an unsupported format.")
    if isinstance(stale_flag, str) and stale_flag.strip().lower() not in {"true", "false", "yes", "no", "1", "0", ""}:
        raise QuoteValidationError("Provider stale flag has an unsupported format.")

    raw_age = payload.get("quoteAgeSeconds")
    if raw_age not in (None, ""):
        if isinstance(raw_age, bool):
            raise QuoteValidationError("Provider quote age metadata is invalid.")
        try:
            provider_age = float(raw_age)
        except (TypeError, ValueError):
            raise QuoteValidationError("Provider quote age metadata is invalid.")
        if not math.isfinite(provider_age) or provider_age < 0:
            raise QuoteValidationError("Provider quote age metadata is invalid.")
        if provider_age > max_age_seconds:
            raise QuoteValidationError(
                f"Provider quote is stale ({int(provider_age)} seconds old by provider metadata; limit {max_age_seconds})."
            )

    bid = _positive_number(payload, "bid", "Bid", "price", "rate", "last", "lastPrice", "mid", "Mid")
    ask = _positive_number(payload, "ask", "Ask", "askPrice")
    if bid is None and ask is None:
        raise QuoteValidationError("No recognizable positive numeric price was returned.")
    if bid is not None and ask is not None and ask < bid:
        raise QuoteValidationError("Ask is below bid; rejecting crossed or inconsistent quote.")

    raw_stamp = next((payload.get(k) for k in (
        "timestamp", "lastQuoteAt", "time", "updated_at", "datetime", "date"
    ) if payload.get(k) not in (None, "")), None)
    parsed_stamp = _parse_timestamp(raw_stamp)
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        current = current.replace(tzinfo=timezone.utc)
    current = current.astimezone(timezone.utc)
    if raw_stamp is not None and parsed_stamp is None:
        raise QuoteValidationError("Provider timestamp is present but could not be parsed.")
    if parsed_stamp is not None:
        age = (current - parsed_stamp).total_seconds()
        if age > max_age_seconds:
            raise QuoteValidationError(f"Provider quote is stale ({int(age)} seconds old; limit {max_age_seconds}).")
        if age < -max_future_skew_seconds:
            raise QuoteValidationError("Provider timestamp is too far in the future.")

    return {
        "symbol": symbol,
        "bid": bid,
        "ask": ask,
        "timestamp": parsed_stamp.isoformat() if parsed_stamp else "Provider did not supply a timestamp; freshness cannot be verified",
        "timestamp_verified": parsed_stamp is not None,
        "received_at": current.isoformat(),
        "source": str(payload.get("source") or "BiQuote public market-data API"),
        "market_state": payload.get("marketState"),
        "mid": _positive_number(payload, "mid", "Mid"),
    }


def fetch_quote_payload(symbol: str) -> Any:
    """Fetch one provider payload with bounded network time; never fabricate fallback data."""
    import requests

    response = requests.get(
        f"https://biquote.io/api/{symbol}",
        headers={"Accept": "application/json", "User-Agent": "SILKOUS-Forex-Intelligence/1.0"},
        timeout=8,
    )
    response.raise_for_status()
    try:
        return response.json()
    except ValueError as exc:
        raise QuoteValidationError("Provider response was not valid JSON.") from exc
