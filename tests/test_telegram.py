import json
import os
import unittest
from unittest.mock import patch

from messaging.telegram import (
    MAX_MESSAGE_LENGTH,
    TelegramConfigError,
    TelegramDeliveryError,
    send_telegram_alert,
)


class _FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class TelegramAlertTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "ARC_SILK_TELEGRAM_BOT_TOKEN": "1234567890:" + "a" *  thirty_chars(),
            "ARC_SILK_TELEGRAM_CHAT_ID": "-1001234567890",
        }, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    @patch("messaging.telegram.urlopen")
    def test_sends_message_and_returns_message_id(self, urlopen):
        urlopen.return_value = _FakeResponse({"ok": True, "result": {"message_id": 42}})
        result = send_telegram_alert("EURUSD BUY | score 84 | RR 1:2")
        self.assertEqual(result, "42")
        request = urlopen.call_args.args[0]
        self.assertEqual(request.method, "POST")
        self.assertNotIn("1234567890:", request.full_url.split("/sendMessage")[0])
        payload = json.loads(request.data.decode("utf-8"))
        self.assertEqual(payload["chat_id"], "-1001234567890")
        self.assertEqual(payload["text"], "EURUSD BUY | score 84 | RR 1:2")
        self.assertTrue(payload["disable_web_page_preview"])

    @patch.dict(os.environ, {"ARC_SILK_TELEGRAM_BOT_TOKEN": "", "ARC_SILK_TELEGRAM_CHAT_ID": ""})
    def test_missing_credentials_fail_closed(self):
        with self.assertRaises(TelegramConfigError):
            send_telegram_alert("test")

    @patch.dict(os.environ, {"ARC_SILK_TELEGRAM_CHAT_ID": "not-a-chat-id"})
    def test_invalid_chat_id_fails_closed(self):
        with self.assertRaises(TelegramConfigError):
            send_telegram_alert("test")

    def test_empty_and_oversized_messages_are_rejected(self):
        with self.assertRaises(ValueError):
            send_telegram_alert("  ")
        with self.assertRaises(ValueError):
            send_telegram_alert("x" * (MAX_MESSAGE_LENGTH + 1))

    @patch("messaging.telegram.urlopen")
    def test_api_rejection_does_not_report_success(self, urlopen):
        urlopen.return_value = _FakeResponse({"ok": False, "description": "Forbidden"})
        with self.assertRaises(TelegramDeliveryError):
            send_telegram_alert("test")

    @patch("messaging.telegram.urlopen")
    def test_response_without_message_id_is_rejected(self, urlopen):
        urlopen.return_value = _FakeResponse({"ok": True, "result": {}})
        with self.assertRaises(TelegramDeliveryError):
            send_telegram_alert("test")

    @patch("messaging.telegram.urlopen", side_effect=TimeoutError("secret details"))
    def test_network_error_is_sanitized(self, urlopen):
        with self.assertRaises(TelegramDeliveryError) as caught:
            send_telegram_alert("test")
        self.assertNotIn("secret details", str(caught.exception))


def thirty_chars():
    return "b" * 30


if __name__ == "__main__":
    unittest.main()
