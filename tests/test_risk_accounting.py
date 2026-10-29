import unittest

from risk_accounting import calculate_risk_normalized_equity


class RiskNormalizedEquityTests(unittest.TestCase):
    def test_one_risk_sized_stop_loss_loses_risk_budget(self):
        result = calculate_risk_normalized_equity(
            [{"entry": 100.0, "stop": 99.0, "net_return_pct": -1.0}],
            risk_per_trade_pct=0.25,
        )
        self.assertAlmostEqual(result["compounded_return_pct"], -0.25)
        self.assertAlmostEqual(result["max_drawdown_pct"], 0.25)
        self.assertFalse(result["execution_allowed"])
        self.assertAlmostEqual(result["profit_factor"], 0.0)

    def test_profit_twice_stop_distance(self):
        result = calculate_risk_normalized_equity(
            [{"entry": 100.0, "stop": 99.0, "net_return_pct": 2.0}],
            risk_per_trade_pct=0.25,
        )
        self.assertAlmostEqual(result["compounded_return_pct"], 0.5)
        self.assertEqual(result["win_rate_pct"], 100.0)
        self.assertEqual(result["profit_factor"], float("inf"))

    def test_compounds_sequentially_and_tracks_drawdown(self):
        result = calculate_risk_normalized_equity(
            [
                {"entry": 100.0, "stop": 99.0, "net_return_pct": 2.0},
                {"entry": 100.0, "stop": 99.0, "net_return_pct": -1.0},
            ],
            risk_per_trade_pct=0.25,
        )
        self.assertAlmostEqual(result["ending_equity"], 1.005 * 0.9975)
        self.assertGreater(result["max_drawdown_pct"], 0)
        self.assertAlmostEqual(result["profit_factor"], 2.0)

    def test_risk_above_gate_limit_can_be_measured_but_gate_must_reject_it(self):
        result = calculate_risk_normalized_equity(
            [], risk_per_trade_pct=0.75
        )
        self.assertEqual(result["risk_per_trade_pct"], 0.75)
        self.assertFalse(result["execution_allowed"])

    def test_rejects_missing_trade_fields(self):
        with self.assertRaises(ValueError):
            calculate_risk_normalized_equity([{"entry": 1.0, "stop": 0.9}])

    def test_rejects_impossible_loss_beyond_full_equity(self):
        with self.assertRaises(ValueError):
            calculate_risk_normalized_equity(
                [{"entry": 100.0, "stop": 99.0, "net_return_pct": -500.0}],
                risk_per_trade_pct=1.0,
            )


if __name__ == "__main__":
    unittest.main()
