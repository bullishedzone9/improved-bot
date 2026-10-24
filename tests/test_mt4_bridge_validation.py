import unittest
from datetime import datetime, timezone, timedelta

from mt4_bridge_validation import TelemetryValidationError, validate_mt4_telemetry


class MT4TelemetryValidationTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
        self.payload = {
            "schema_version": "1",
            "event_time": self.now.isoformat(),
            "symbol": "EURUSD",
            "bid": 1.1000,
            "ask": 1.1002,
            "spread_points": 2.0,
            "sequence": 4,
        }

    def test_valid_payload_is_normalized(self):
        result = validate_mt4_telemetry(
            self.payload, allowed_symbols={"EURUSD"}, now=self.now
        )
        self.assertEqual(result["symbol"], "EURUSD")
        self.assertEqual(result["bid"], 1.1)
        self.assertTrue(result["fresh"])

    def test_rejects_symbol_not_allowlisted(self):
        with self.assertRaises(TelemetryValidationError):
            validate_mt4_telemetry(
                self.payload, allowed_symbols={"GBPUSD"}, now=self.now
            )

    def test_rejects_crossed_market(self):
        payload = dict(self.payload, bid=1.101, ask=1.100)
        with self.assertRaises(TelemetryValidationError):
            validate_mt4_telemetry(payload, now=self.now)

    def test_rejects_stale_payload(self):
        payload = dict(
            self.payload,
            event_time=(self.now - timedelta(seconds=31)).isoformat(),
        )
        with self.assertRaises(TelemetryValidationError):
            validate_mt4_telemetry(payload, now=self.now)

    def test_rejects_non_finite_price(self):
        payload = dict(self.payload, bid=float("nan"))
        with self.assertRaises(TelemetryValidationError):
            validate_mt4_telemetry(payload, now=self.now)

    def test_rejects_timezone_naive_timestamp(self):
        payload = dict(self.payload, event_time="2026-10-24T12:00:00")
        with self.assertRaises(TelemetryValidationError):
            validate_mt4_telemetry(payload, now=self.now)


if __name__ == "__main__":
    unittest.main()
