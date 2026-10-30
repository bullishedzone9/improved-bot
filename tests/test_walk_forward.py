import unittest

import pandas as pd

from walk_forward import evaluate_walk_forward


class WalkForwardTests(unittest.TestCase):
    def prices(self, n=240):
        # Deterministic varying series, for mechanics only—not market evidence.
        return pd.Series([1.10 + i * 0.0001 + ((i % 11) - 5) * 0.00008 for i in range(n)])

    def test_returns_chronological_train_and_holdout_reports(self):
        result = evaluate_walk_forward(self.prices())
        self.assertEqual(result["status"], "RESEARCH_ONLY")
        self.assertEqual(result["strategy"], "SMA_LONG_OR_CASH")
        self.assertEqual(result["train_bars"], 168)
        self.assertEqual(result["out_of_sample_bars"], 72)
        self.assertEqual(result["out_of_sample"]["periods"], 72)
        self.assertIn("profit_factor", result["out_of_sample"])

    def test_rejects_short_history(self):
        with self.assertRaises(ValueError):
            evaluate_walk_forward(self.prices(59))

    def test_rejects_invalid_windows(self):
        with self.assertRaises(ValueError):
            evaluate_walk_forward(self.prices(), fast_window=50, slow_window=20)

    def test_rejects_invalid_split(self):
        with self.assertRaises(ValueError):
            evaluate_walk_forward(self.prices(), train_fraction=0.4)

    def test_rejects_nonpositive_or_nonfinite_prices(self):
        bad = self.prices()
        bad.iloc[10] = float("nan")
        with self.assertRaises(ValueError):
            evaluate_walk_forward(bad)


if __name__ == "__main__":
    unittest.main()
