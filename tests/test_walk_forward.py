import unittest

from walk_forward import evaluate_chronological_split


def sample_candles(count=240):
    rows = []
    previous = 1.10
    for i in range(count):
        # Deterministic synthetic data for logic tests, not market data.
        close = 1.10 + i * 0.0001 + (0.0015 if (i // 12) % 2 else -0.0015)
        open_price = previous
        high = max(open_price, close) + 0.0005
        low = min(open_price, close) - 0.0005
        rows.append({"open": open_price, "high": high, "low": low, "close": close})
        previous = close
    return rows


class WalkForwardTests(unittest.TestCase):
    def test_chronological_split_reports_test_metrics_and_never_execution(self):
        result = evaluate_chronological_split(sample_candles())
        self.assertEqual(result["mode"], "RESEARCH_WALK_FORWARD_ONLY")
        self.assertFalse(result["order_sent"])
        self.assertFalse(result["execution_allowed"])
        self.assertGreater(result["split_index"], 0)
        self.assertEqual(result["train"]["bars"] + result["out_of_sample"]["bars"], 240)
        self.assertIn("profit_factor", result["out_of_sample"])
        self.assertIn("risk_normalized_profit_factor", result["out_of_sample"])
        self.assertIn("risk_normalized_max_drawdown_pct", result["out_of_sample"])
        self.assertIn("risk_normalized_compounded_return_pct", result["out_of_sample"])
        self.assertFalse(result["out_of_sample"]["risk_normalized_mode"] == "")

    def test_rejects_invalid_fraction(self):
        with self.assertRaisesRegex(ValueError, "train_fraction"):
            evaluate_chronological_split(sample_candles(), train_fraction=0.4)

    def test_rejects_insufficient_history(self):
        with self.assertRaisesRegex(ValueError, "at least"):
            evaluate_chronological_split(sample_candles(80))


if __name__ == "__main__":
    unittest.main()
