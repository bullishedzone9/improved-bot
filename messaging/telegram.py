"""Opt-in Telegram alert sender for qualified forex signals.

Credentials are read only from server-side environment variables. This module
never places broker orders and is not called automatically by the scanner.
"""
from __future__ import annotations

import json
import os
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


MAX_MESSAGE_LENGTH = 3900
_CHAT_ID_RE = re.compile(r"^-?\d{1,20}$")


class TelegramConfigError(RuntimeError):
    """Telegram credentials or destination are missing or invalid."""


class TelegramDeliveryError(RuntimeError):
    """Telegram rejected the request or delivery could not be confirmed."""


def send_telegram_alert(message: str, *, timeout: float = 10.0) -> str:
    """Send one explicitly requested message and return Telegram's message id.

    Required environment variables:
      ARC_SILK_TELEGRAM_BOT_TOKEN
      ARC_SILK_TELEGRAM_CHAT_ID

    Do not log or expose the token. A successful API response means Telegram
    accepted the message; it does not guarantee the recipient viewed it.
    """
    token = os.environ.get("ARC_SILK_TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("ARC_SILK_TELEGRAM_CHAT_ID", "").strip()
    if not token or len(token) < 20:
        raise TelegramConfigError("Telegram bot token is not configured")
    if not _CHAT_ID_RE.fullmatch(chat_id):
        raise TelegramConfigError("Telegram chat ID is missing or invalid")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("message must be a non-empty string")
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValueError(f"message exceeds {MAX_MESSAGE_LENGTH} characters")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": message.strip(),
        "disable_web_page_preview": True,
    }).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError):
        raise TelegramDeliveryError("Telegram request failed") from None

    if not isinstance(data, dict) or data.get("ok") is not True:
        raise TelegramDeliveryError("Telegram did not accept the alert")
    result = data.get("result")
    message_id = result.get("message_id") if isinstance(result, dict) else None
    if not isinstance(message_id, int):
        raise TelegramDeliveryError("Telegram response lacked a message ID")
    return str(message_id)
