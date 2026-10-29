import unittest

from strategy_gates import evaluate_strategy_gates


class StrategyGateTests(unittest.TestCase):
    def test_missing_out_of_sample_evidence_fails_closed(self):
        result = evaluate_strategy_gates(
            profit_factor=1.5,
            max_drawdown_pct=5.0,
            out_of_sample_return_pct=None,
            risk_per_trade_pct=0.25,
            daily_loss_limit_pct=2.0,
        )
        self.assertFalse(result["passed"])
        self.assertFalse(result["execution_allowed"])
        self.assertIn("Out-of-sample return after costs", result["failed_checks"])

    def test_all_thresholds_met_passes_research_gate_only(self):
        result = evaluate_strategy_gates(
            profit_factor=1.35,
            max_drawdown_pct=8.0,
            out_of_sample_return_pct=3.0,
            risk_per_trade_pct=0.5,
            daily_loss_limit_pct=2.0,
        )
        self.assertTrue(result["passed"])
        self.assertFalse(result["execution_allowed"])

    def test_current_style_of_poor_metrics_fails(self):
        result = evaluate_strategy_gates(
            profit_factor=0.83,
            max_drawdown_pct=49.07,
            out_of_sample_return_pct=-5.0,
            risk_per_trade_pct=0.5,
            daily_loss_limit_pct=2.0,
        )
        self.assertFalse(result["passed"])
        self.assertIn("Profit factor", result["failed_checks"])
        self.assertIn("Maximum drawdown", result["failed_checks"])
        self.assertIn("Out-of-sample return after costs", result["failed_checks"])

    def test_rejects_invalid_risk_and_nonfinite_metrics(self):
        with self.assertRaisesRegex(ValueError, "risk_per_trade_pct"):
            evaluate_strategy_gates(
                profit_factor=1.5,
                max_drawdown_pct=5.0,
                out_of_sample_return_pct=1.0,
                risk_per_trade_pct=float("nan"),
                daily_loss_limit_pct=2.0,
            )
        with self.assertRaisesRegex(ValueError, "profit_factor"):
            evaluate_strategy_gates(
                profit_factor=float("inf"),
                max_drawdown_pct=5.0,
                out_of_sample_return_pct=1.0,
                risk_per_trade_pct=0.25,
                daily_loss_limit_pct=2.0,
            )


if __name__ == "__main__":
    unittest.main()
