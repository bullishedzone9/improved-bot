import unittest

import pandas as pd

from backtest import run_moving_average_backtest


class MovingAverageBacktestTests(unittest.TestCase):
    def test_empty_input_is_rejected(self):
        with self.assertRaises(ValueError):
            run_moving_average_backtest(pd.Series(dtype=float), pd.Series(dtype=float), pd.Series(dtype=float))

    def test_invalid_cost_is_rejected(self):
        close = pd.Series([1.0, 1.1, 1.2])
        ma = pd.Series([1.0, 1.0, 1.0])
        with self.assertRaises(ValueError):
            run_moving_average_backtest(close, ma, ma, -1)

    def test_nonpositive_or_nonfinite_prices_are_rejected(self):
        ma = pd.Series([1.0, 1.0, 1.0])
        with self.assertRaises(ValueError):
            run_moving_average_backtest(pd.Series([1.0, 0.0, 1.2]), ma, ma)
        with self.assertRaises(ValueError):
            run_moving_average_backtest(pd.Series([1.0, float("inf"), 1.2]), ma, ma)

    def test_outputs_are_finite_and_equity_starts_at_one(self):
        close = pd.Series([1.0, 1.01, 1.02, 1.00, 1.04, 1.06, 1.05])
        fast = pd.Series([float("nan"), 1.0, 1.01, 1.01, 1.02, 1.03, 1.04])
        slow = pd.Series([float("nan"), float("nan"), 1.0, 1.01, 1.01, 1.02, 1.03])
        result = run_moving_average_backtest(close, fast, slow, 2)
        self.assertAlmostEqual(float(result["equity_curve"].iloc[0]), 1.0)
        self.assertAlmostEqual(float(result["benchmark_curve"].iloc[0]), 1.0)
        self.assertTrue(result["equity_curve"].map(pd.notna).all())
        self.assertTrue(result["drawdown"].le(1e-12).all())
        self.assertGreaterEqual(result["completed_trades"], 0)
        self.assertEqual(result["completed_trades"], len(result["trade_returns"]))

    def test_cost_reduces_or_does_not_improve_strategy_return(self):
        close = pd.Series([1.0, 1.1, 1.2, 1.1, 1.3, 1.25, 1.4])
        fast = pd.Series([1.0, 1.1, 1.2, 1.1, 1.3, 1.25, 1.4])
        slow = pd.Series([1.1, 1.1, 1.1, 1.2, 1.2, 1.3, 1.3])
        free = run_moving_average_backtest(close, fast, slow, 0)
        costly = run_moving_average_backtest(close, fast, slow, 10)
        self.assertLessEqual(costly["strategy_return"], free["strategy_return"] + 1e-12)


if __name__ == "__main__":
    unittest.main()
