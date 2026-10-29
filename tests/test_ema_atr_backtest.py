import unittest

from ema_atr_backtest import backtest_ema_atr


def bars(closes):
    return [
        {"open": close, "high": close + 0.2, "low": close - 0.2, "close": close}
        for close in closes
    ]


class EmaAtrBacktestTests(unittest.TestCase):
    def test_flat_series_has_no_trades_and_never_sends_orders(self):
        result = backtest_ema_atr(
            bars([10.0] * 12),
            fast_period=2,
            slow_period=3,
            atr_period=2,
        )
        self.assertEqual(result["mode"], "PAPER_BACKTEST_ONLY")
        self.assertEqual(result["trade_count"], 0)
        self.assertEqual(result["win_rate_pct"], 0.0)
        self.assertFalse(result["order_sent"])

    def test_rejects_insufficient_history(self):
        with self.assertRaisesRegex(ValueError, "need at least"):
            backtest_ema_atr(
                bars([10, 11, 12]),
                fast_period=2,
                slow_period=5,
                atr_period=2,
            )

    def test_rejects_negative_costs(self):
        with self.assertRaisesRegex(ValueError, "costs cannot be negative"):
            backtest_ema_atr(
                bars([10.0] * 12),
                fast_period=2,
                slow_period=3,
                atr_period=2,
                cost_bps_per_side=-1,
            )


if __name__ == "__main__":
    unittest.main()
