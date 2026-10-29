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

    def test_crossover_enters_next_bar_and_stop_precedes_target(self):
        candles = bars([10.0, 10.0, 10.0, 10.0, 10.0, 10.5])
        candles.append({"open": 10.5, "high": 13.5, "low": 8.0, "close": 12.0})
        result = backtest_ema_atr(
            candles, fast_period=2, slow_period=3, atr_period=2,
            cost_bps_per_side=0,
        )
        self.assertFalse(result["order_sent"])
        self.assertGreaterEqual(result["trade_count"], 1)
        trade = result["trades"][0]
        self.assertEqual(trade["side"], "BUY")
        self.assertEqual(trade["entry_index"], trade["signal_index"] + 1)
        self.assertEqual(trade["exit_reason"], "STOP")


if __name__ == "__main__":
    unittest.main()
