import unittest

import pandas as pd

from backtest import run_moving_average_backtest


class MovingAverageBacktestTests(unittest.TestCase):
    def test_empty_input_is_rejected(self):
        empty = pd.Series(dtype=float)
        with self.assertRaises(ValueError):
            run_moving_average_backtest(empty, empty, empty)

    def test_invalid_cost_is_rejected(self):
        values = pd.Series([1.0, 1.1, 1.2])
        for cost in (-1, 101, float("inf"), True):
            with self.subTest(cost=cost), self.assertRaises(ValueError):
                run_moving_average_backtest(values, values, values, cost)

    def test_nonpositive_or_nonfinite_prices_are_rejected(self):
        ma = pd.Series([1.0, 1.0, 1.0])
        for prices in ([1.0, 0.0, 1.2], [1.0, float("inf"), 1.2], [1.0, float("nan"), 1.2]):
            with self.subTest(prices=prices), self.assertRaises(ValueError):
                run_moving_average_backtest(pd.Series(prices), ma, ma)

    def test_moving_average_infinity_and_length_mismatch_are_rejected(self):
        close = pd.Series([100.0, 101.0, 102.0])
        slow = pd.Series([99.0, 99.0, 99.0])
        with self.assertRaises(ValueError):
            run_moving_average_backtest(close, pd.Series([100.0, float("inf"), 101.0]), slow)
        with self.assertRaises(ValueError):
            run_moving_average_backtest(close, pd.Series([100.0]), slow)

    def test_signal_is_delayed_one_bar(self):
        close = pd.Series([100.0, 110.0, 121.0, 110.0, 100.0, 110.0])
        fast = pd.Series([2.0, 2.0, 0.0, 0.0, 2.0, 2.0])
        slow = pd.Series([1.0] * 6)
        result = run_moving_average_backtest(close, fast, slow, 0)
        self.assertEqual(result["position"].tolist(), [0, 1, 1, 0, 0, 1])
        self.assertAlmostEqual(result["strategy_period_returns"].iloc[1], 0.10)
        self.assertAlmostEqual(result["strategy_period_returns"].iloc[2], 0.10)
        self.assertAlmostEqual(result["strategy_period_returns"].iloc[3], 0.0)

    def test_entry_and_exit_costs_are_each_charged_once(self):
        close = pd.Series([100.0, 110.0, 121.0, 110.0, 100.0])
        fast = pd.Series([2.0, 2.0, 2.0, 0.0, 0.0])
        slow = pd.Series([1.0] * 5)
        result = run_moving_average_backtest(close, fast, slow, 10)
        self.assertEqual(result["position"].tolist(), [0, 1, 1, 1, 0])
        self.assertAlmostEqual(result["strategy_period_returns"].iloc[1], 0.10 - 0.001)
        self.assertAlmostEqual(result["strategy_period_returns"].iloc[2], 0.10)
        self.assertAlmostEqual(result["strategy_period_returns"].iloc[3], 110.0 / 121.0 - 1.0)
        self.assertAlmostEqual(result["strategy_period_returns"].iloc[4], -0.001)
        self.assertEqual(result["completed_trades"], 1)
        expected_trade_return = (1.099 * 1.1 * (110.0 / 121.0) * 0.999) - 1.0
        self.assertAlmostEqual(result["trade_returns"][0], expected_trade_return)

    def test_open_trade_at_end_is_not_counted_as_completed(self):
        close = pd.Series([100.0, 110.0, 120.0])
        fast = pd.Series([2.0] * 3)
        slow = pd.Series([1.0] * 3)
        result = run_moving_average_backtest(close, fast, slow, 0)
        self.assertEqual(result["position"].tolist(), [0, 1, 1])
        self.assertEqual(result["completed_trades"], 0)
        self.assertEqual(result["trade_returns"], [])

    def test_max_drawdown_is_calculated_from_equity_peaks(self):
        close = pd.Series([100.0, 110.0, 99.0, 120.0])
        fast = pd.Series([2.0] * 4)
        slow = pd.Series([1.0] * 4)
        result = run_moving_average_backtest(close, fast, slow, 0)
        self.assertAlmostEqual(result["max_drawdown"], -0.10)
        self.assertAlmostEqual(float(result["drawdown"].min()), -0.10)
        self.assertTrue(result["drawdown"].le(1e-12).all())

    def test_equity_curves_start_at_one_and_costs_do_not_improve_return(self):
        close = pd.Series([1.0, 1.1, 1.2, 1.1, 1.3, 1.25, 1.4])
        fast = pd.Series([1.0, 1.1, 1.2, 1.1, 1.3, 1.25, 1.4])
        slow = pd.Series([1.1, 1.1, 1.1, 1.2, 1.2, 1.3, 1.3])
        free = run_moving_average_backtest(close, fast, slow, 0)
        costly = run_moving_average_backtest(close, fast, slow, 10)
        self.assertAlmostEqual(float(free["equity_curve"].iloc[0]), 1.0)
        self.assertAlmostEqual(float(free["benchmark_curve"].iloc[0]), 1.0)
        self.assertLessEqual(costly["strategy_return"], free["strategy_return"] + 1e-12)
        self.assertEqual(costly["completed_trades"], len(costly["trade_returns"]))

    def test_strategy_return_is_nonincreasing_as_transaction_costs_rise(self):
        close = pd.Series([100, 103, 101, 105, 99, 104, 98, 106, 102], dtype=float)
        fast = pd.Series([2, 2, 0, 2, 0, 2, 0, 2, 2], dtype=float)
        slow = pd.Series([1] * len(close), dtype=float)
        returns = [
            run_moving_average_backtest(close, fast, slow, cost)["strategy_return"]
            for cost in (0, 2, 10, 50, 100)
        ]
        self.assertTrue(all(later <= earlier + 1e-12 for earlier, later in zip(returns, returns[1:])))

    def test_flat_market_has_zero_benchmark_return_and_no_positive_gross_edge(self):
        close = pd.Series([100.0] * 8)
        fast = pd.Series([2.0, 2.0, 0.0, 2.0, 0.0, 2.0, 2.0, 0.0])
        slow = pd.Series([1.0] * 8)
        result = run_moving_average_backtest(close, fast, slow, 10)
        self.assertAlmostEqual(result["benchmark_return"], 0.0)
        self.assertLessEqual(result["strategy_return"], 0.0)
        self.assertTrue(result["equity_curve"].map(lambda value: pd.notna(value) and value > 0).all())

    def test_output_curves_preserve_input_length_for_short_and_long_samples(self):
        for length in (1, 3, 30, 250):
            close = pd.Series([100.0 + i * 0.1 for i in range(length)])
            fast = close.rolling(3, min_periods=1).mean()
            slow = close.rolling(5, min_periods=1).mean()
            result = run_moving_average_backtest(close, fast, slow, 2)
            with self.subTest(length=length):
                self.assertEqual(len(result["equity_curve"]), length)
                self.assertEqual(len(result["benchmark_curve"]), length)
                self.assertEqual(len(result["drawdown"]), length)
                self.assertTrue(result["equity_curve"].map(pd.notna).all())
                self.assertTrue(result["benchmark_curve"].map(pd.notna).all())
                self.assertLessEqual(result["max_drawdown"], 1e-12)
                self.assertGreaterEqual(result["max_drawdown"], -1.0)

if __name__ == "__main__":
    unittest.main()
