import unittest

from paper_engine import atr, ema, evaluate_signal, validate_candles


def bars(closes):
    return [
        {"open": close, "high": close + 0.2, "low": close - 0.2, "close": close}
        for close in closes
    ]


class PaperEngineTests(unittest.TestCase):
    def test_ema_has_warmup_and_smooths(self):
        result = ema([1, 2, 3, 4], 2)
        self.assertIsNone(result[0])
        self.assertAlmostEqual(result[1], 1.5)
        self.assertAlmostEqual(result[2], 2.5)

    def test_atr_uses_true_range_after_first_bar(self):
        result = atr(bars([10, 11, 12]), 2)
        self.assertIsNone(result[0])
        self.assertAlmostEqual(result[1], 0.6)
        self.assertAlmostEqual(result[2], 1.0)

    def test_upward_crossover_returns_buy_but_never_sends_order(self):
        result = evaluate_signal(
            bars([10, 10, 10, 10, 10, 10, 12]),
            fast_period=2,
            slow_period=3,
            atr_period=2,
        )
        self.assertEqual(result["signal"], "BUY")
        self.assertEqual(result["mode"], "PAPER_ONLY")
        self.assertFalse(result["order_sent"])
        self.assertGreater(result["stop_distance"], 0)
        self.assertAlmostEqual(result["target_distance"], result["stop_distance"] * 2)

    def test_flat_market_returns_flat(self):
        result = evaluate_signal(
            bars([10] * 8), fast_period=2, slow_period=3, atr_period=2
        )
        self.assertEqual(result["signal"], "FLAT")
        self.assertFalse(result["order_sent"])

    def test_rejects_bad_ohlc_and_insufficient_history(self):
        with self.assertRaisesRegex(ValueError, "inconsistent high"):
            validate_candles([{"open": 10, "high": 9, "low": 8, "close": 9}])
        with self.assertRaisesRegex(ValueError, "need at least"):
            evaluate_signal(bars([10, 11, 12]), fast_period=2, slow_period=5, atr_period=2)

    def test_rejects_invalid_periods(self):
        with self.assertRaises(ValueError):
            ema([1, 2, 3], 1)
        with self.assertRaises(ValueError):
            evaluate_signal(bars([10] * 8), fast_period=3, slow_period=3, atr_period=2)


if __name__ == "__main__":
    unittest.main()
