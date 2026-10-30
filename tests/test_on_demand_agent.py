import unittest

from on_demand_agent.engine import ScreeningConfig, screen_market


class OnDemandScreeningTests(unittest.TestCase):
    def setUp(self):
        self.candles = [
            {"high": 1.101 + i * 0.0001, "low": 1.099 + i * 0.0001,
             "close": 1.100 + i * 0.0001}
            for i in range(60)
        ]

    def call_screen(self, **overrides):
        args = dict(
            candles=self.candles, bid=1.1050, ask=1.1052,
            quote_age_seconds=1, spread_points=2, point=0.0001,
            daily_loss_percent=0,
        )
        args.update(overrides)
        return screen_market(**args)

    def test_stale_quote_fails_closed(self):
        result = self.call_screen(quote_age_seconds=31)
        self.assertEqual(result.status, "NO_TRADE")
        self.assertEqual(result.reason, "STALE_QUOTE")

    def test_wide_spread_fails_closed(self):
        result = self.call_screen(spread_points=26)
        self.assertEqual(result.reason, "SPREAD_TOO_WIDE")

    def test_daily_loss_lock_fails_closed(self):
        result = self.call_screen(daily_loss_percent=1.0)
        self.assertEqual(result.reason, "DAILY_LOSS_LOCK")

    def test_insufficient_candles_fails_closed(self):
        result = self.call_screen(candles=self.candles[:10])
        self.assertEqual(result.reason, "INSUFFICIENT_CLOSED_CANDLES")

    def test_risk_configuration_cannot_exceed_cap(self):
        with self.assertRaises(ValueError):
            ScreeningConfig(risk_percent=0.5).validate()

    def test_invalid_quote_fails_closed(self):
        result = self.call_screen(bid=1.2, ask=1.1)
        self.assertEqual(result.reason, "INVALID_QUOTE")

    def test_no_order_execution_surface(self):
        result = self.call_screen()
        self.assertNotIn("order_id", result.to_dict())
        self.assertIn(result.status, {"CANDIDATE", "NO_TRADE"})


if __name__ == "__main__":
    unittest.main()
