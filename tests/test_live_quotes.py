import unittest
from datetime import datetime, timezone, timedelta

from live_quotes import QuoteValidationError, validate_quote


class LiveQuoteValidationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)

    def test_valid_quote_and_iso_timestamp(self):
        result = validate_quote({"bid": "1.1000", "ask": "1.1002", "timestamp": self.now.isoformat()}, "EURUSD", now=self.now)
        self.assertEqual(result["bid"], 1.1)
        self.assertAlmostEqual(result["ask"] - result["bid"], 0.0002)
        self.assertTrue(result["timestamp_verified"])

    def test_valid_unix_milliseconds(self):
        stamp = int(self.now.timestamp() * 1000)
        result = validate_quote({"mid": 1.1, "timestamp": stamp}, "EURUSD", now=self.now)
        self.assertEqual(result["bid"], 1.1)

    def test_missing_timestamp_is_explicitly_unverified(self):
        result = validate_quote({"price": 1.1}, "EURUSD", now=self.now)
        self.assertFalse(result["timestamp_verified"])
        self.assertIn("cannot be verified", result["timestamp"])

    def test_rejects_stale_timestamp(self):
        stale = (self.now - timedelta(minutes=4)).isoformat()
        with self.assertRaisesRegex(QuoteValidationError, "stale"):
            validate_quote({"price": 1.1, "timestamp": stale}, "EURUSD", now=self.now)

    def test_rejects_provider_stale_flag(self):
        with self.assertRaisesRegex(QuoteValidationError, "explicitly marks.*stale"):
            validate_quote({"bid": 1.1, "ask": 1.1002, "timestamp": self.now.isoformat(), "stale": True}, "EURUSD", now=self.now)

    def test_rejects_provider_quote_age_metadata(self):
        with self.assertRaisesRegex(QuoteValidationError, "stale"):
            validate_quote({"bid": 1.1, "ask": 1.1002, "timestamp": self.now.isoformat(), "quoteAgeSeconds": 77734}, "EURUSD", now=self.now)

    def test_accepts_fresh_provider_metadata(self):
        result = validate_quote({"bid": 1.1, "ask": 1.1002, "timestamp": self.now.isoformat(), "stale": False, "quoteAgeSeconds": 12}, "EURUSD", now=self.now)
        self.assertEqual(result["bid"], 1.1)

    def test_uses_last_quote_at_timestamp(self):
        result = validate_quote({"mid": 1.1, "lastQuoteAt": self.now.isoformat()}, "EURUSD", now=self.now)
        self.assertTrue(result["timestamp_verified"])

    def test_rejects_future_timestamp(self):
        future = (self.now + timedelta(minutes=2)).isoformat()
        with self.assertRaisesRegex(QuoteValidationError, "future"):
            validate_quote({"price": 1.1, "timestamp": future}, "EURUSD", now=self.now)

    def test_rejects_crossed_quote(self):
        with self.assertRaisesRegex(QuoteValidationError, "Ask is below bid"):
            validate_quote({"bid": 1.2, "ask": 1.1}, "EURUSD", now=self.now)

    def test_rejects_bad_timestamp(self):
        with self.assertRaisesRegex(QuoteValidationError, "could not be parsed"):
            validate_quote({"price": 1.1, "timestamp": "not-a-date"}, "EURUSD", now=self.now)

    def test_rejects_bad_price_and_multiple_rows(self):
        for payload in ({"bid": 0}, {"bid": float("inf")}, [{"price": 1.1}, {"price": 1.2}], None):
            with self.subTest(payload=payload), self.assertRaises(QuoteValidationError):
                validate_quote(payload, "EURUSD", now=self.now)


if __name__ == "__main__":
    unittest.main()
