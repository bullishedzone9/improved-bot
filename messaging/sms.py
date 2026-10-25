"""Opt-in SMS notifications for SILKOUS Forex Intelligence.

This module sends a text only when an application explicitly calls send_sms().
It does not place trades, poll markets, or send unsolicited messages.
Configure credentials as server-side environment variables; never commit them.
"""
from __future__ import annotations

import os
import re
from typing import NamedTuple

import requests


class SmsResult(NamedTuple):
    sent: bool
    message: str


_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def send_sms(to_number: str, message: str) -> SmsResult:
    """Send one SMS through Twilio; fail closed when configuration is missing."""
    account_sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    auth_token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    from_number = os.getenv("TWILIO_FROM_NUMBER", "").strip()

    if not (account_sid and auth_token and from_number):
        return SmsResult(False, "SMS is not configured; no message was sent.")
    if not _E164.fullmatch(to_number.strip()) or not _E164.fullmatch(from_number):
        return SmsResult(False, "Phone numbers must use E.164 format, e.g. +2348012345678.")
    if not message or not message.strip():
        return SmsResult(False, "Message is empty; no message was sent.")
    if len(message) > 1500:
        return SmsResult(False, "Message exceeds the 1500-character safety limit.")

    url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
    try:
        response = requests.post(
            url,
            auth=(account_sid, auth_token),
            data={"To": to_number.strip(), "From": from_number, "Body": message.strip()},
            timeout=12,
        )
        if response.status_code not in (200, 201):
            # Do not return response body; it may contain provider/account details.
            return SmsResult(False, f"SMS provider rejected the request (HTTP {response.status_code}).")
        return SmsResult(True, "SMS accepted by provider.")
    except requests.RequestException:
        return SmsResult(False, "SMS provider could not be reached; delivery is unconfirmed.")
